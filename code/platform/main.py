from fastapi import FastAPI, File, UploadFile
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from kafka_bootstrap import kafka_bootstrap
from cassandra_bootstrap import create_cassandra_table
import os

app = FastAPI()

origins = ["http://localhost:5173"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# client need to provide this
data_constrain_ingest = {
    "key_space": "mysimbdp_coredms",
    "schema": {
        "name": "analytics",
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
            {"name": "fare", "type": "int"},
            {"name": "tips", "type": "float"},
            {"name": "tolls", "type": "int"},
            {"name": "extras", "type": "int"},
            {"name": "trip_total", "type": "float"},
            {"name": "payment_type", "type": "string"},
            {"name": "company", "type": "string"},
            {"name": "pickup_centroid_latitude", "type": "float"},
            {"name": "pickup_centroid_longitude", "type": "float"},
            {"name": "pickup_centroid_location", "type": "string"},
            {"name": "dropoff_centroid_latitude", "type": "float"},
            {"name": "dropoff_centroid_longitude", "type": "float"},
            {"name": "dropoff_centroid_location", "type": "string"}
        ]
    },
    "primary_key": ["taxi_id", "trip_id"]
}

data_constrain_trips_total = {
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

data_constrain_sum_fare_window = {
    "key_space": "mysimbdp_coredms",
    "schema": {
        "name": "sumfarewindow",
        "fields": [
            {"name": "id", "type": "uuid"},
            {"name": "window", "type": "string"},
            {"name": "total_fare", "type": "float"},
            {"name": "tips_fare", "type": "float"},
            {"name": "total_trip_total", "type": "float"}
        ]
    },
    "primary_key": ["id"]
}

data_constrain_hotspot_window = {
    "key_space": "mysimbdp_coredms",
    "schema": {
        "name": "hotspotwindow",
        "fields": [
            {"name": "id", "type": "uuid"},
            {"name": "window", "type": "string"},
            {"name": "pickup_centroid_location", "type": "string"},
            {"name": "count", "type": "int"}
        ]
    },
    "primary_key": ["id"]
}

data_constrain_hotspot_community_window = {
    "key_space": "mysimbdp_coredms",
    "schema": {
        "name": "hotspotcommunitywindow",
        "fields": [
            {"name": "id", "type": "uuid"},
            {"name": "window", "type": "string"},
            {"name": "pickup_community_area", "type": "string"},
            {"name": "count", "type": "int"}
        ]
    },
    "primary_key": ["id"]
}


async def on_startup():
    [await create_cassandra_table(
        item["schema"],
        keyspace="mysimbdp_coredms",
        primary_key=item["primary_key"],
    ) for item in
     [data_constrain_ingest, data_constrain_trips_total, data_constrain_sum_fare_window, data_constrain_hotspot_window,
      data_constrain_hotspot_community_window]]

    await kafka_bootstrap()


app.add_event_handler("startup", on_startup)

# Directory to save the uploaded files
UPLOAD_DIR = "client-staging-input-directory"


@app.get("/tenant/{tenant_id}")
def read_root(tenant_id: str):
    # Create the directory if it doesn't exist
    upload_dir = f"{UPLOAD_DIR}/{tenant_id}/in"
    if not os.path.exists(upload_dir):
        os.makedirs(upload_dir, exist_ok=True)

    files = os.listdir(f"{UPLOAD_DIR}/{tenant_id}/in")
    return files


@app.post("/upload-file/{tenant_id}")
async def create_upload_file(tenant_id: str, file: UploadFile = File(...)):
    try:
        upload_dir = f"{UPLOAD_DIR}/{tenant_id}/in"
        file_path = os.path.join(upload_dir, file.filename)

        # Save the file
        with open(file_path, "wb") as buffer:
            buffer.write(file.file.read())

        return JSONResponse(
            content={"message": "File uploaded successfully", "file_path": file_path}
        )
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)
