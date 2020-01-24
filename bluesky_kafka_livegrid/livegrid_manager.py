import argparse
import pprint

from bluesky.callbacks.mpl_plotting import LiveGrid

from bluesky_kafka_livegrid.live_server import live_server


class LiveGridManager:
    def __init__(self):
        self.live_grids = dict()
        self.descriptor_uid_to_run_uid = dict()

    def __call__(self, name, doc):
        if name == "start":
            print(f"starting a LiveGrid for run {doc['uid']}")
            pprint.pprint(doc)
            run_start_uid = doc["uid"]
            self.live_grids[run_start_uid] = LiveGrid(raster_shape=(10, 10), I="det")
            self.live_grids[run_start_uid].start(doc)
        elif name == "descriptor":
            print("descriptor:")
            pprint.pprint(doc)
            self.descriptor_uid_to_run_uid[doc["uid"]] = doc["run_start"]
        elif name == "event":
            print("event:")
            pprint.pprint(doc)
            run_uid = self.descriptor_uid_to_run_uid[doc["descriptor"]]
            livegrid = self.live_grids[run_uid]
            livegrid.event(doc)
        elif name == "stop":
            print("stop:")
            pprint.pprint(doc)
        else:
            print(name)


if __name__ == "__main__":
    argparser = argparse.ArgumentParser()
    argparser.add_argument("topics")
    argparser.add_argument("bootstrap-servers")
    argparser.add_argument("group-id")

    args = argparser.parse_args()
    print(args)

    manager = LiveGridManager()

    live_server(manager=manager, **vars(args))
