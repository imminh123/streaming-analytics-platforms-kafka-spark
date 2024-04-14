from confluent_kafka.admin import AdminClient, NewTopic

APP_NAME = "tenantstreamapp"
KAFKA_HOST = "localhost:19092"


async def kafka_bootstrap(kafka_host=KAFKA_HOST, app_name=APP_NAME):
    # Specify the Kafka broker(s) as a list of bootstrap servers

    # Create an AdminClient instance
    admin_client = AdminClient({"bootstrap.servers": kafka_host})

    # Specify the topic name and other configuration options

    num_partitions = 1
    replication_factor = 1
    config = {"cleanup.policy": "compact"}

    kafka_connect_topics = ["bdp-platform-config", "bdp-platform-status", "bdp-platform-offsets"]
    topics = [f"{app_name}_ingestData", f"{app_name}_tripsTotalStream", f"{app_name}_sumFareWindowStream",
              f"{app_name}_hotspotCommunityPickupWindowStream", f"{app_name}_hotspotWindowStream"]

    kafka_topics = [
        NewTopic(
            topic=topic_name,
            num_partitions=num_partitions,
            replication_factor=replication_factor,
        )
        for topic_name in topics
    ]

    kafka_connect_topics = [
        NewTopic(
            topic=topic_name,
            num_partitions=num_partitions,
            replication_factor=replication_factor,
            config=config
        )
        for topic_name in kafka_connect_topics
    ]

    # Create the topic using the create_topics method
    fs = admin_client.create_topics(kafka_topics + kafka_connect_topics)

    for topic, f in fs.items():
        try:
            f.result()  # The result itself is None
            print("Topic {} created".format(topic))
        except Exception as e:
            print("Failed to create topic {}: {}".format(topic, e))
