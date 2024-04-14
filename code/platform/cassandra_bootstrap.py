from cassandra.cluster import Cluster


async def create_cassandra_table(avro_schema, keyspace, primary_key):
    print(avro_schema)
    # Connect to Cassandra cluster
    cluster = Cluster(["127.0.0.1"])
    session = cluster.connect()

    # Create Keyspace if not exists
    session.execute(
        f"CREATE KEYSPACE IF NOT EXISTS {keyspace} WITH replication = {{'class': 'SimpleStrategy', 'replication_factor': 3}}"
    )

    # Switch to the specified keyspace
    session.set_keyspace(keyspace)

    # Create a table based on the Avro schema
    query = (
        f"CREATE TABLE IF NOT EXISTS {avro_schema['name']} {avro_schema_to_cql(avro_schema, primary_key)};"
    )
    session.execute(query)

    # Close the Cassandra session and cluster connection
    session.shutdown()
    cluster.shutdown()


def avro_schema_to_cql(avro_schema, primary_key):
    fields = avro_schema["fields"]
    cql_columns = [
        f'{field["name"]} {avro_type_to_cql(field["type"][1] if isinstance(field["type"], list) else field["type"])}'
        for field in fields
    ]

    # Add primary key specification
    if primary_key:
        cql_columns.append(f'PRIMARY KEY ({", ".join(primary_key)})')

    return f"({', '.join(cql_columns)})"


def avro_type_to_cql(avro_type):
    if avro_type == "int":
        return "int"
    elif avro_type == "long":
        return "bigint"
    elif avro_type == "double":
        return "double"
    elif avro_type == "float":
        return "float"
    elif avro_type == "string":
        return "text"
    elif avro_type == "uuid":
        return "uuid"
    else:
        raise ValueError(f"Unsupported Avro type: {avro_type}")
