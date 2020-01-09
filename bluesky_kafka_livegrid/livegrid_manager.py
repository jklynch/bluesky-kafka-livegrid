import pprint

import msgpack

from bluesky_kafka.kafka import RemoteDispatcher


class LiveGridManager:
    def __init__(self):
        self.live_plots = dict()

    def __call__(self, name, doc):
        if name == "start":
            print(f"starting a LiveGrid for run {doc['uid']}")
            run_start_uuid = doc["uid"]
        elif name == "descriptor":
            print("descriptor:")
            pprint.pprint(doc)
        elif name == "event":
            print("event:")
            pprint.pprint(doc)
        elif name == "stop":
            print("stop:")
            pprint.pprint(doc)
        else:
            print(name)


def livegrid_server():
    dispatcher = RemoteDispatcher(
        topics=["srx-bluesky"],
        bootstrap_servers="10.5.0.18:9092",
        group_id="livegrid",
        #deserializer=msgpack.unpackb,
    )

    manager = LiveGridManager()

    dispatcher.subscribe(func=manager)

    dispatcher.start()


if __name__ == "__main__":
    livegrid_server()
