# This is a deployment/installation guide

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


