from pyspark.sql import SparkSession
from pyspark.sql.functions import from_json, col, count, sum, avg, current_timestamp, window, round, current_date, \
    concat, lit, date_add
from pyspark.sql.types import StructType, StringType, TimestampType, DoubleType, IntegerType

APP_NAME = "tenantstreamapp"
KAFKA_HOST = "localhost:19092"

spark = (
    SparkSession.builder.appName(APP_NAME)
    .config("spark.streaming.stopGracefullyOnShutdown", True)
    .config("spark.jars.packages", "org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.1")
    .master("local[2]")
    .getOrCreate()
)
spark.catalog.clearCache()


def return_write_stream(df, topic, mode, name):
    return df.writeStream.outputMode(mode).format("kafka").queryName(name).option("kafka.bootstrap.servers",
                                                                                  KAFKA_HOST).option(
        "topic", f"{APP_NAME}_{topic}").option("checkpointLocation", f"/tmp/checkpoints_2/{topic}").start()


schema = StructType().add("trip_id", StringType(), True) \
    .add("taxi_id", StringType(), True) \
    .add("trip_start_timestamp", TimestampType(), True) \
    .add("trip_end_timestamp", TimestampType(), True) \
    .add("trip_seconds", IntegerType(), True) \
    .add("trip_miles", DoubleType(), True) \
    .add("pickup_census_tract", DoubleType(), True) \
    .add("dropoff_census_tract", DoubleType(), True) \
    .add("pickup_community_area", IntegerType(), True) \
    .add("dropoff_community_area", DoubleType(), True) \
    .add("fare", DoubleType(), True) \
    .add("tips", DoubleType(), True) \
    .add("tolls", DoubleType(), True) \
    .add("extras", DoubleType(), True) \
    .add("trip_total", DoubleType(), True) \
    .add("payment_type", StringType(), True) \
    .add("company", StringType(), True) \
    .add("pickup_centroid_latitude", DoubleType(), True) \
    .add("pickup_centroid_longitude", DoubleType(), True) \
    .add("pickup_centroid_location", StringType(), True) \
    .add("dropoff_centroid_latitude", DoubleType(), True) \
    .add("dropoff_centroid_longitude", DoubleType(), True) \
    .add("dropoff_centroid_location", StringType(), True) \
    .add("event_timestamp", TimestampType(), True)

# Create DataFrame representing the stream of input lines from connection to localhost:9999
df = (
    spark.readStream.format("kafka")
    .option("kafka.bootstrap.servers", KAFKA_HOST)
    .option("subscribe", f"{APP_NAME}_ingestData")
    .option("failOnDataLoss", "false")
    .option("startingOffsets", "latest")
    .load()
)

base_df = df.selectExpr("CAST(key AS STRING)", "CAST(value AS STRING)", "timestamp")

info_df = base_df.select(from_json(col("value"), schema).alias("trip_schema"), "timestamp")
info_df_fin = info_df.select("trip_schema.*", "timestamp")

# fare distribution
sum_fare_window = info_df_fin.withWatermark("event_timestamp", "10 seconds").groupBy(
    window("event_timestamp", "5 seconds")).agg(round(sum("fare"), 0).alias("total_fare"),
                                                round(sum("tips"), 0).alias("tips_fare"),
                                                round(sum("trip_total"), 0).alias(
                                                    "total_trip_total")).selectExpr(
    "to_json(struct(*)) AS value")
sum_fare_window_stream = return_write_stream(sum_fare_window, "sumFareWindowStream", "update", "sum_fare_window_stream_2")

# total so far
today = current_date()
specific_time = "00:00:00"  # Change this to your specific time
specific_date_time = concat(today, lit(" "), lit(specific_time)).cast("timestamp")
specific_time_data = info_df_fin.filter(col("event_timestamp") > specific_date_time) \
    .filter(col("event_timestamp") < date_add(today, 1))

trips_total = specific_time_data.select(count("*").alias("trips_total"), round(sum("fare"), 0).alias("fare_total"),
                                        round(avg("tips"), 0).alias("tips_avg"),
                                        round(avg("trip_total"), 0).alias("trip_total_avg")).selectExpr(
    "to_json(struct(*)) AS value")
trips_total_stream = return_write_stream(trips_total, "tripsTotalStream", "complete", "trips_total_stream_2")

# hot spot pickup community area
hot_spot_community_pickup_window = info_df_fin.withWatermark("event_timestamp", "10 seconds").groupBy(
    window("event_timestamp", "1 minute", "30 seconds"), "pickup_community_area").count().filter(
    col("pickup_community_area").isNotNull()).selectExpr(
    "to_json(struct(*)) AS value")
hot_spot_community_pickup_window_stream = return_write_stream(hot_spot_community_pickup_window,
                                                              "hotspotCommunityPickupWindowStream", "append",
                                                              "hot_spot_community_pickup_window_stream_2")

# hot spot pickup location
hot_spot_window = info_df_fin.withWatermark("event_timestamp", "10 seconds").groupBy(
    window("event_timestamp", "1 minute", "30 seconds"), "pickup_centroid_location").count().selectExpr(
    "to_json(struct(*)) AS value")
hot_spot_window_stream = return_write_stream(hot_spot_window, "hotspotWindowStream", "append", "hot_spot_window_stream_2")

sum_fare_window_stream.awaitTermination()
hot_spot_window_stream.awaitTermination()
hot_spot_community_pickup_window_stream.awaitTermination()
trips_total_stream.awaitTermination()
