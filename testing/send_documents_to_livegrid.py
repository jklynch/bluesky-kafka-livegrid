import argparse
import datetime
import logging

from bluesky_kafka.kafka import Publisher
from event_model import compose_run


logging.basicConfig(level=logging.DEBUG)


"""
Start a Kafka broker.
    ./bin/zookeeper-server-start.sh ./config/zookeeper.properties
    ./bin/kafka-server-start.sh ./config/server.properties
Add the necessary topics:
    ./bin/kafka-topics.sh --create --zookeeper localhost:2181 --replication-factor 1 --partitions 1 --topic srx.bluesky.documents
Start livegrid_manager.py
Start send_documents_to_livegrid.py
"""


def send_documents(topic, bootstrap_servers):
    print("send documents to kafka broker")
    kafka_publisher = Publisher(
        topic=topic, bootstrap_servers=bootstrap_servers, key="testing"
    )

    run_start_doc, compose_desc, compose_resource, compose_stop = compose_run()
    kafka_publisher("start", run_start_doc)

    # copied from run 588bed89-b8e9-4882-86b2-c9471612914e at SRX
    event_descriptor_doc, compose_event, compose_event_page = compose_desc(
        data_keys={
            "ROI_01": {
                "source": "PV:XF:05IDD-ES{Xsp:1}:C1_ROI1:Value_RBV",
                "dtype": "number",
                "shape": [],
                "precision": 4,
                "units": "",
                "lower_ctrl_limit": 0.0,
                "upper_ctrl_limit": 0.0,
            }
        },
        configuration={
            "ROI_01": {
                "data": {"ROI_01": 6201.48337647908},
                "timestamps": {"ROI_01": 1572730676.801648},
                "data_keys": {
                    "ROI_01": {
                        "source": "PV:XF:05IDD-ES{Xsp:1}:C1_ROI1:Value_RBV",
                        "dtype": "number",
                        "shape": [],
                        "precision": 4,
                        "units": "",
                        "lower_ctrl_limit": 0.0,
                        "upper_ctrl_limit": 0.0,
                    }
                },
            }
        },
        name="ROI_01_monitor",
        object_keys={"ROI_01": ["ROI_01"]},
    )
    kafka_publisher("descriptor", event_descriptor_doc)

    for _ in range(10):
        event_doc = compose_event(
            data={'ROI_01': 5.0},
            timestamps={"ROI_01": 1572730676.801648},
        )
        kafka_publisher("event", event_doc)

    run_stop_doc = compose_stop()
    kafka_publisher("stop", run_stop_doc)


if __name__ == "__main__":
    argparser = argparse.ArgumentParser()
    argparser.add_argument("--topic", type=str, default="srx.bluesky.documents")
    argparser.add_argument("--bootstrap-servers", type=str, help="comma-delimited list")

    args = argparser.parse_args()
    print(args)

    send_documents(**vars(args))
