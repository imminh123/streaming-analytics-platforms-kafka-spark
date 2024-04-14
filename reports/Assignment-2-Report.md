# Part 1 - Design for streaming analytics

## 1. Dataset
As a tenant, we will choose the dataset of [Taxi Trips by City of Chicago (2013-2023)](https://data.cityofchicago.org/Transportation/Taxi-Trips-2013-2023-/wrvz-psew/about_data) as a running scenario. This dataset contains information about taxi trip records from 2013 to 2023 reported to the City of Chicago.
With 23 attributes for each data point, including trip duration, distance, location of pickup and dropoff, fares, etc, streaming analytics can provide valuable insights for operations, customer preference that ultimately contribute to the decision making process, improving overall service quality. 

| Trip ID                        | Taxi ID                                                                                        | Trip Start Timestamp   | Trip End Timestamp     | Trip Seconds | Trip Miles | Pickup Census Tract | Dropoff Census Tract | Pickup Community Area | Dropoff Community Area | Fare  | Tips | Tolls | Extras | Trip Total | Payment Type | Company      | Pickup Centroid Latitude | Pickup Centroid Longitude | Pickup Centroid Location            | Dropoff Centroid Latitude | Dropoff Centroid Longitude | Dropoff Centroid Location           |
|--------------------------------|------------------------------------------------------------------------------------------------|------------------------|------------------------|--------------|------------|---------------------|----------------------|-----------------------|------------------------|-------|------|-------|--------|------------|--------------|--------------|--------------------------|---------------------------|------------------------------------|---------------------------|----------------------------|------------------------------------|
| 0002044d | 476c001 | 01/22/2024 01:45:00 PM | 01/22/2024 02:00:00 PM | 841          | 2.2        |                     |                      | 8                     | 28                     | 10.25 | 4.00 | 0.00  | 1.00   | 15.75      | Credit Card  | City Service | 41.899602111             | -87.633308037             | POINT (-87.6333080367 41.899602111) | 41.874005383              | -87.66351755              | POINT (-87.6635175498 41.874005383) |

Some of the valuable insights can be analyzed from this dataset include:

### Streaming Analytics 
- Total metrics in a window: calculating the total of several metrics (fare, tips, trips total) for a window of time (daily), operators can see the peak hours when demand is high, base on that adjust fleet availability and pricing strategy.
- Accumulated business metrics so far in a day: calculating accumulated number of trip, fare and average tips, total so far in a day, providing a real-time view of daily business performance.
- Hot spot for pickup community area: Chicago has 77 communities area, and the information about pickup community area are also provided. This can be used to identify popular areas for pickup, useful for resource allocation.
- Hot spot for pickup location: using geo-location, we can specify popular places for pickup, increase dispatch efficiency.

### Batch Analytics 
- Trends and patterns in fare distribution: based on historical analyzed result on daily fare distribution, company can analyze the overal trends and patterns over different time windows (monthly, quarterly, annualy), and further optimize service performance/quality.
- Accumulated business metrics: aggregating daily metrics on trip, fare, tips to calculate the accumulated revenue in a wider time window (monthly, annualy). This information can be used to make strategic decisions and adjust operational strategies.
- Hot spot for pickup community area: based on historical data on popular community area, operator can identify persistent hot spots, and further analyze factors contributing to their popularity (proximity to attraction, population, etc).
- Hot spot for pickup location: the aggregated historical data can give more accurate data on frequency of pick-ups at each location, combine with study on factors contributing to their popularity to optimize dispatching algorithms, route planning, and resource allocation for drivers.



## 2. Data Constrains
### Keyed or Non-keyed Data Streams 
For our tenant usecase, since the analytic data does not rely on operations that require grouping, aggregating or processing based on any specific attributes, we treat all events EQUALLY. Hence, our streaming analytics platform only deals with **Non-keyed Data Streams**. 


### Message Delivery Guarantees
**Expected throughput**: Base on [previous analysis](https://toddwschneider.com/posts/chicago-taxi-data/) conducted, the number of taxi trips per day in Chicago averages around 50k to 100k during normal day and peaked at 150k on holiday occasions like St. Patrick's Day Parade. With our sample dataset, there are around 55k taxi trip records per day. *With the amount of events, we expected this fall into the comfort zone of our messaging system levering Kafka.*

**The importance of a single message**: One taxi record is packed with useful informatin that directly contributes to the company's decision at the time on pricing, resource allocation and optimization. Hence, an appropriate semantic guarantee should prioritize *durability* and *consistency*.

With these considerations on tenant data, our messaging system should support the Message Delivery Guarantees level of [**Exactly Once** on both producer and consumer (utilize Kafka transactional delivery)](https://docs.confluent.io/kafka/design/delivery-semantics.html). With this, each message is delivered once and only once. Messages are never lost or read twice even if some part of the system fails.

## 3. Time, Windows, Out-of-order, and Watermarks
### Event Time
In order to produce useful insights as the tenant has defined, and guarantee the **real-time** characteristic associated with the real world, it is mandatory that our data sources come with **Event Time** for each record. This refers to the time when a taxi trip actually occurred in the real world. Fortunately, the tenant's dataset has already come with 2 timestamp attribute of *Trip Start Timestamp* and *Trip End Timestamp*.

### Windows
Different operations will handle different types of window on analytic data. 
1. **Total metrics in a window**: as this operation aims to calculate fare distribution in a fixed non-overlap period of time, a tumbling window of `5 seconds` base on `event_timestamp` is used.
2. **Accumulated business metrics so far in a day**: No window needed as this operation aims to provide a real-time view into business performance, new results will be added to previous one, thus the task will run as soon as possible.
3. **Hot spot for pickup community area**: the operation calculate the occurrence of community areas for the past period of time (1 minute), thus using a *sliding* window of `1 minute` for every `30 seconds` base on `event_timestamp`.
4. **Hot spot for pickup location**: same as the above, this operation calculate the occurrence of popular pickup locations for the past period of time (1 minute), thus using a *sliding* window of `1 minute` for every `30 seconds` base on `event_timestamp`.

### Out-of-order data
Several reasons that can cause out-of-order data include:
1. Network delay/latency: our whole platform is designed with distribute components, thus relies on network to communicate. Any network delay can cause data to arrived out-of-order. This can happen at all stages of the pipeline (data source publish/consume, data sink publish/consume).
2. Processing delay: depend on the factor of parallelism and resources allocated to Kafka (partitions) and Spark (maximum tasks) that one slow task can cause out-of-order for subsequent records.
3. Out-of-order source: even though in our example, emulated data is guaranteed having ordered event time assigned for each record, in real life scenario, data can be out-of-order from the source.

### Watermarks
Since several of our operations relies on aggregating data for a specify time window, it's mandatory for Spark application to enforce watermarking to address the issue of out-of-order data and ensure correct results for window-based operations.

## 4. Performance metrics
Important performance metrics that our tenant need to be aware include metrics collected from the platform' message brokers (Kafka) and the streaming analytic engine (Sparl). Here are some of the important metrics (non-exhaustive list) and how our platform helps tenant in measuring it.
1. Data Throughput
2. Resource Utilization

# Part 2 - Implementation of streaming analytics
The following documentation addresses the implementation of the **tenantstreamapp** - an Spark application developed by client for real-time streaming analytics (structured streaming).

## 1. Data Structures and Schemas

### Schemas
For both input and output data, schemas defining the data structures and types are strictly enforced, for the following reasons:
1. The data sink of our platform relies on Cassandra, thus tables need to be created beforehand based on pre-defined schemas.
2. Our platform uses middleware that need to explicitly define the data structure, like Kafka Connect for Cassandra requires mapping config from Topics to Tables.
3. Schema provide a standard view to manage and validate schemas used by producers and consumers. With pre-defined schemas, our platform can use [Schema Registry](https://docs.confluent.io/platform/current/schema-registry/index.html#:~:text=Schema%20Registry%20provides%20a%20centralized,and%20compatibility%20as%20schemas%20evolve.) to further enforce them for input data and results.

#### Example
One of the output data schema is *tripstotal* (sum of several business metrics) need to explicitly define its schema, using **Avro** format.
```
{
    "key_space": "mysimbdp_coredms",
    "schema": {
        "name": "tripstotal",
        "fields": [
            {"name": "id", "type": "uuid"},
            {"name": "trips_total", "type": "int"},
            {"name": "fare_total", "type": "float"},
            {"name": "tips_avg", "type": "float"},
            {"name": "trip_total_avg", "type": "float"}
        ]
    },
    "primary_key": ["id"]
}
```

Our input data is about taxi trip records, and the ingested data also need to define the schema in Avro format as below.
```
{
    "key_space": "mysimbdp_coredms",
    "schema": {
        "name": "ingestData",
        "fields": [
            {"name": "trip_id", "type": "string"},
            {"name": "taxi_id", "type": "string"},
            {"name": "trip_start_timestamp", "type": "string"},
            {"name": "trip_end_timestamp", "type": "string"},
            {"name": "trip_seconds", "type": "int"},
            {"name": "trip_miles", "type": "float"},
            {"name": "pickup_census_tract", "type": ["null", "long"]},
            {"name": "dropoff_census_tract", "type": ["null", "long"]},
            {"name": "pickup_community_area", "type": ["null", "int"]},
            {"name": "dropoff_community_area", "type": ["null", "int"]},
            <!-- continue -->
        ]
    },
    "primary_key": ["taxi_id", "trip_id"]
}
```

### Serialization/deserialization
According to [Spark documentation on structured streaming](https://spark.apache.org/docs/2.2.2/structured-streaming-kafka-integration.html):
> key.deserializer: Keys are always deserialized as byte arrays with ByteArrayDeserializer. <br>
value.deserializer: Values are always deserialized as byte arrays with ByteArrayDeserializer.

Thus, for our producer using Kafka, the data also needs to be serialize with a format suitable with Spark's **ByteArrayDeserializer**. For simplicity, we will go with **UTF-8 encoding**, which text data will be represented as a sequence of bytes, or a byte array, making it compatible with **ByteArrayDeserializer**.  

## 2. Processing Functions

### Total metrics in a window for fare distribution
#### Logic
Calculate total amount of:
1. fare (total_fare)
2. tips (tips_fare)
3. trip_total (total_trip_total)
> The result of this function can be use to plot the fare distribution through out the day. Based on that, operators can see the peak hours when all the fares increase significantly, represented by spikes in the distribution.

![Fare distribution](https://global.discourse-cdn.com/grafana/original/3X/8/c/8c987edc27f6505a4434a2a940bd5e63f2b1786a.png)
#### Configuration
The function aggregate data from a tumbling window of `5 seconds` base on `event_timestamp`, with watermarking accepts delay up to 10 seconds. The aggregated output will be write into another Kafka topic named `{tenant_app_name}_sumFareWindowStream`. The data in this topic will be written to our Cassandra sink table `sumfarewindow` by a Kafka connect consumer.

#### Code
```
# fare distribution
sum_fare_window = info_df_fin.withWatermark("event_timestamp", "10 seconds").groupBy(
    window("event_timestamp", "5 seconds")).agg(round(sum("fare"), 2).alias("total_fare"),
                                                    round(sum("tips"), 2).alias("tips_fare"),
                                                    round(sum("trip_total"), 2).alias(
                                                        "total_trip_total")).selectExpr(
    "to_json(struct(*)) AS value")
sum_fare_window_stream = return_write_stream(sum_fare_window, "sumFareWindowStream", "update", "sum_fare_window_stream")
```

#### Sample output
```
{
  "window": {
    "start": "2024-04-13T19:48:15.000+03:00",
    "end": "2024-04-13T19:48:20.000+03:00"
  },
  "total_fare": 242,
  "tips_fare": 46.6,
  "total_trip_total": 313.6
}
```


### Accumulated number of trip, fare and average tips, total so far in a day (starting from 00:00 to 23:59)
#### Logic
Calculate accumulated and average amount of:
1. trips (trips_total)
2. fare (fare_total)
3. average tips (tips_avg)
4. average trip_total (trip_total_avg)
> The result of this function provide a real-time view of business performance in a day, showing daily revenue, total number of trips, average tips and trip total fare can somehow reflect the service quality.

![Total metrics so far](https://questdb.io/img/blog/2024-01-15/nyc-cab-3.gif)

#### Configuration
The data as input for this function need to be filtered based on the condition `00:00` > `event_timestamp` < `23:59`.
The function aggregate data as soon as possible. Using `complete` output mode, new results will be added to previous one. The output will be write into another Kafka topic named `{tenant_app_name}_tripsTotalStream`. The data in this topic will be written to our Cassandra sink table `tripstotal` by a Kafka connect consumer.

#### Code
```
# total so far
today = current_date()
specific_time = "00:00:00"  # Change this to your specific time
specific_date_time = concat(today, lit(" "), lit(specific_time)).cast("timestamp")
specific_time_data = info_df_fin.filter(col("event_timestamp") > specific_date_time) \
                               .filter(col("event_timestamp") < date_add(today, 1))

trips_total = specific_time_data.select(count("*").alias("trips_total"), round(sum("fare"), 2).alias("fare_total"),
                                 round(avg("tips"), 2).alias("tips_avg"), round(avg("trip_total"), 2).alias("trip_total_avg")).selectExpr(
    "to_json(struct(*)) AS value")
trips_total_stream = return_write_stream(trips_total, "tripsTotalStream", "complete", "trips_total_stream")
```

#### Sample output
```
{
  "trips_total": 19747,
  "fare_total": 350466.95,
  "tips_avg": 3.13,
  "trip_total_avg": 22.53
}
```

### Hot spot for pickup community area
#### Logic
Count the number of `pickup_community_area` in a period of time (last 1 minute) for every 30 seconds.
> The result can be used to form a heatmap of popular community areas having high demand for taxi. 

![Geomap Grafana](https://awsopensourceblog.s3.us-east-2.amazonaws.com/assets/alolitas_geomap_plugin_grafana/alolitas_geomap_plugin_grafana_f12.png)

#### Configuration  
The function aggregate data from a *sliding* window of `1 minute` for every `30 seconds` base on `event_timestamp`, with watermarking accepts delay up to `10 seconds`. The output will be written into another Kafka topic named `{tenant_app_name}_hotspotCommunityPickupWindowStream`. The data in this topic will be written to our Cassandra sink table `hotspotcommunitywindow` by a Kafka connect consumer.

#### Code
```
# hot spot pickup community area
hot_spot_community_pickup_window = info_df_fin.withWatermark("event_timestamp", "10 seconds").groupBy(
    window("event_timestamp", "1 minute", "30 seconds"), "pickup_community_area").count().selectExpr(
    "to_json(struct(*)) AS value")
hot_spot_community_pickup_window_stream = return_write_stream(hot_spot_community_pickup_window,
                                                              "hotspotCommunityPickupWindowStream", "append", "hot_spot_community_pickup_window_stream")
```

#### Sample output
```
{
  "window": {
    "start": "2024-04-13T19:48:00.000+03:00",
    "end": "2024-04-13T19:49:00.000+03:00"
  },
  "pickup_community_area": 28,
  "count": 7
}
```

### Hot spot for pickup location
#### Logic
Count the number of `pickup_centroid_location` in a period of time (last 1 minute) for every 30 seconds.
> The result can be used to form a heatmap of popular pickup location. 

![Geomap Grafana](https://grafana.com/static/img/docs/geomap-panel/geomap-markers-8-1-0.png)

#### Configuration  
The function aggregate data from a *sliding* window of `1 minute` for every `30 seconds` base on `event_timestamp`, with watermarking accepts delay up to `10 seconds`. The output will be written into another Kafka topic named `{tenant_app_name}_hotspotWindowStream`. The data in this topic will be written to our Cassandra sink table `hotspotwindow` by a Kafka connect consumer.

#### Code
```
# hot spot pickup location
hot_spot_window = info_df_fin.withWatermark("event_timestamp", "10 seconds").groupBy(
    window("event_timestamp", "1 minute", "30 seconds"), "pickup_centroid_location").count().selectExpr(
    "to_json(struct(*)) AS value")
hot_spot_window_stream = return_write_stream(hot_spot_window, "hotspotWindowStream", "append", "hot_spot_window_stream")
```

#### Sample output
```
{
  "window": {
    "start": "2024-04-13T19:48:00.000+03:00",
    "end": "2024-04-13T19:49:00.000+03:00"
  },
  "pickup_centroid_location": "POINT (-87.6266589003 41.9075200747)",
  "count": 1
}
```

## 3. 