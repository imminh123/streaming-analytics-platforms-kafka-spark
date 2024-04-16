# Real-time streaming analytics application with Spark and Kafka.
A sample real-time streaming analytics application with Spark Structured Streaming and Kafka.

## System architecture 
### Design
![Kafka Spark architect design](https://github.com/imminh123/streaming-analytics-platforms-kafka-spark/blob/main/assets/kafka_spark.png?raw=true)

### Architecture Breakdown
1. **Tenant data sources**: In reality, our system will take real-time taxi trips data ingested by tenant system via specified Kafka topics. 

To emulate this data, we use CSV files report from tenant. As a platform provider, we will created needed resources (topics, tables) base on provided schemas and a custom application to ingest CSV file to our Kafka message broker.

2. Messaging system: our platform relies on Kafka for messaging system for its massive scalability, high throughput and low latency, thus suitable with the characteristic of our tenant application (real-time analytic to optimize business operation timely)

3. Streaming computing service: The choice for Spark comes naturally as our tenant will eventually need the ability for batch processing from our platform, and Spark wears two hats (stream and batch). Also Spark is known for its speed (process data in-memory), ease of use with high-level API (structured streaming) making it easier for implementing `tenantstreamapp`.

4. Coredms: analytic results will be ingested to `mysimbdp-coredms` from a Kafka Connect cluster with Cassandra sink connector. 

## Dataset
As a tenant, we will choose the dataset of [Taxi Trips by City of Chicago (2013-2023)](https://data.cityofchicago.org/Transportation/Taxi-Trips-2013-2023-/wrvz-psew/about_data) as a running scenario. This dataset contains information about taxi trip records from 2013 to 2023 reported to the City of Chicago.
With 23 attributes for each data point, including trip duration, distance, location of pickup and dropoff, fares, etc, streaming analytics can provide valuable insights for operations, customer preference that ultimately contribute to the decision making process, improving overall service quality. 

Some of the valuable insights can be analyzed from this dataset include:

### Streaming Analytics 
- Total metrics in a window: calculating the total of several metrics (fare, tips, trips total) for a window of time (daily), operators can see the peak hours when demand is high, base on that adjust fleet availability and pricing strategy.
- Accumulated business metrics so far in a day: calculating accumulated number of trip, fare and average tips, total so far in a day, providing a real-time view of daily business performance.
- Hot spot for pickup community area: Chicago has 77 communities area, and the information about pickup community area are also provided. This can be used to identify popular areas for pickup, useful for resource allocation.
- Hot spot for pickup location: using geo-location, we can specify popular places for pickup, increase dispatch efficiency.

---

# Deployment/installation guide

### Deploy Cassandra Cluster
The docker compose located in `code/docker-compose-cassandra.yaml`
```
docker-compose -f docker-compose-cassandra.yaml up -d
```

### Setting up Cassandra Keyspace
Run FastAPI server, update `data_constrain` variable if you want to use other data files.

```
python code/platform/main.py
```

### Deploy Kafka & Kafka Connect Cluster & Prometheus & Grafana

```
docker-compose up -d
```

Sending GET request to this url to verified we have 1 connectors installed , http://localhost:8083/connectors

```
[
"cassandra-sink"
]
```

Grafana dashboard can be accessed at: http://localhost:3000

### Register Connector to Kafka Connect

**cassandra-sink**

```
curl --location 'http://localhost:8083/connectors' \
--header 'Content-Type: application/json' \
--data '{
    "name": "cassandra-sink",
    "config": {
        "connector.class": "com.datastax.oss.kafka.sink.CassandraSinkConnector",
        "key.converter": "org.apache.kafka.connect.json.JsonConverter",
        "key.converter.schemas.enable": "false",
        "value.converter": "org.apache.kafka.connect.json.JsonConverter",
        "value.converter.schemas.enable": "false",
        "tasks.max": "4",
        "topics": "tenantstreamapp_tripsTotalStream, tenantstreamapp_sumFareWindowStream, tenantstreamapp_hotspotCommunityPickupWindowStream, tenantstreamapp_hotspotWindowStream",
        "contactPoints": "cassandra1",
        "loadBalancing.localDc": "helsinki",
        "port": 9042,
        "ignoreErrors": "None",
        "maxConcurrentRequests": 500,
        "maxNumberOfRecordsInBatch": 32,
        "queryExecutionTimeout": 30,
        "connectionPoolLocalSize": 4,
        "jmx": true,
        "compression": "None",

        "auth.provider": "None",
        "auth.username": "",
        "auth.password": "",
        "auth.gssapi.keyTab": "",
        "auth.gssapi.principal": "",
        "auth.gssapi.service": "dse",
        "ssl.provider": "None",
        "ssl.hostnameValidation": true,
        "ssl.keystore.password": "",
        "ssl.keystore.path": "",
        "ssl.openssl.keyCertChain": "",
        "ssl.openssl.privateKey": "",
        "ssl.truststore.password": "",
        "ssl.truststore.path": "",
        "ssl.cipherSuites": "",
        
         
         "topic.tenantstreamapp_tripsTotalStream.mysimbdp_coredms.tripstotal.mapping": "id=now(),trips_total=value.trips_total,fare_total=value.fare_total,tips_avg=value.tips_avg,trip_total_avg=value.trip_total_avg",
    
        "topic.tenantstreamapp_sumFareWindowStream.mysimbdp_coredms.sumfarewindow.mapping": "id=now(),window=value.window,total_fare=value.total_fare,tips_fare=value.tips_fare,total_trip_total=value.total_trip_total",

        "topic.tenantstreamapp_hotspotWindowStream.mysimbdp_coredms.hotspotwindow.mapping": "id=now(),pickup_centroid_location=value.pickup_centroid_location,count=value.count,window=value.window",

        "topic.tenantstreamapp_hotspotCommunityPickupWindowStream.mysimbdp_coredms.hotspotcommunitywindow.mapping": "id=now(),pickup_community_area=value.pickup_community_area,count=value.count, window=value.window"
    }
}
'
```

### Start tenantstreamapp Spark application
```
python code/tenantstreamapp/main.py
```
Spark dashboard can be accessed at: http://localhost:4040

If you want to run with multi tenants, I've also provide a different tenantstreamapp with different query names but work on the same dataset.
```
python code/tenantstreamapp/main_2.py
```
Spark dashboard can be accessed at: http://localhost:4041

### Emulated data source
```
python kafka_producer.py  -i ../../data/Taxi_Trips__2024-__20240401_min.csv -c 10 -s 0 -t tenantstreamapp_ingestData
```


