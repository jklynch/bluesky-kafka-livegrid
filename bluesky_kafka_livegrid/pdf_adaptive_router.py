import argparse
import logging
import pickle

from confluent_kafka import Producer

import matplotlib.pyplot as plt
import numpy as np

from event_model import DocumentRouter, RunRouter
from bluesky_kafka_livegrid.live_server import live_server
from databroker import Broker

from bluesky.utils import install_kicker

install_kicker()

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("adaptive_router")


"""
(/tmp/adp) xf28id1@xf28id1-ws1:~/adaptive/bluesky-kafka-livegrid/bluesky_kafka_livegrid$ python pdf_adaptive_router.py
"""


class PDFAdaptiveDocumentRouter(DocumentRouter):
    def __init__(self, learner, kafka_producer):
        super().__init__()
        self.learner = learner
        self.kafka_producer = kafka_producer

    def start(self, doc):
        log.debug(f"start: {doc}")

    def descriptor(self, doc):
        log.debug(f"descriptor: {doc}")

    def event(self, doc):
        log.debug(f"event: {doc}")

    def event_page(self, doc):
        log.debug(f"event_page: {doc}")

    def stop(self, doc):
        log.debug(f"stop: {doc}")

        if doc["exit_status"] != "success":
            log.info("abort!")
            return

        log.info("subtracting dark image")
        data_broker = Broker.named("pdf")
        scan_uid = doc["run_start"]
        scan_hdr = data_broker[scan_uid]
        scan_data_table = scan_hdr.table(fill=True)
        scan_image = scan_data_table["pe1c_image"][1]
        scan_grid_x = scan_data_table["Grid_X"][1]
        darkframe_uid = scan_hdr.start["sc_dk_field_uid"]
        darkframe_hdr = data_broker[darkframe_uid]
        darkframe_image = darkframe_hdr.table(fill=True)["pe1c_image"][1]

        darkframe_subtracted_image = scan_image.astype(np.float64) - darkframe_image.astype(np.float64)
        self.learner.tell(scan_grid_x, darkframe_subtracted_image)
        new_x_list, _ = self.learner.ask(1)
        log.info("new_x_list: %s", new_x_list)
        if not len(new_x_list):
            return
        new_x, = new_x_list
        log.info("new_x is %s", new_x)
        self.kafka_producer.produce(
            topic="pdf.bluesky.adaptive",
            key="adaptive_key",
            value=pickle.dumps({"Grid_X": new_x}),
        )
from adaptive import Learner1D

class Learner:
    def __init__(self, grid_x_min, grid_x_max, grid_x_min_step_size, grid_x_max_step_size):
        self.fig, self.ax = plt.subplots()
        plt.show(block=False)
        self.ln, = self.ax.plot([], [], '-o')
        self.real_learner = Learner1D(None, (grid_x_min, grid_x_max))
        self.grid_x_min = grid_x_min
        self.grid_x_max = grid_x_max
        self.grid_x_min_step_size = grid_x_min_step_size
        self.grid_x_max_step_size = grid_x_max_step_size
        self.dark_subtracted_images = []

    def ask(self, n):
        log.info("learner loss is %.5f", self.real_learner.loss())
        if self.real_learner.loss() > .01:
            return self.real_learner.ask(n, tell_pending=False)
        return [], []
        # last_grid_x, _ = self.dark_subtracted_images[-1]
        #
        # new_x = last_grid_x + self.grid_x_max_step_size
        # if self.grid_x_min < new_x < self.grid_x_max:
        #     return [new_x], [0]
        # else:
        #     log.info("time to stop")
        #     return [], []

    def tell(self, x, y):
        self.real_learner.tell(x, (y.sum(),))
        self.dark_subtracted_images.append((x, y.sum()))
        x, y = zip(*self.dark_subtracted_images)
        self.ln.set_data(x, y)
        self.ax.relim()
        self.ax.autoscale_view()
        self.fig.canvas.draw_idle()
        self.fig.canvas.flush_events()
        plt.pause(.1)


if __name__ == "__main__":
    argparser = argparse.ArgumentParser()
    argparser.add_argument("--topics", default="pdf.bluesky.documents")
    argparser.add_argument("--bootstrap-servers", default="10.0.137.8:9092")
    argparser.add_argument("--group-id", default="pdf_adaptive_router")

    args = argparser.parse_args()
    print(args)

    learner_ = Learner(
        grid_x_min=65.0,
        grid_x_max=75.0,
        grid_x_min_step_size=0.5,
        grid_x_max_step_size=1.0
    )

    producer_config = {
        "bootstrap.servers": args.bootstrap_servers,
        "acks": 1,
    }
    kafka_producer_ = Producer(producer_config)

    # factory('start', start_doc) -> List[Callbacks], List[SubFactories]
    def adaptive_document_router_factory(start_doc_name, start_doc):
        # create a DocumentRouter only for "adaptive_group" scans
        if "adaptive_group" in start_doc:
            log.info("we have an adaptive_group scan")
            pdf_adaptive_document_router = PDFAdaptiveDocumentRouter(
                learner=learner_,
                kafka_producer=kafka_producer_)
            pdf_adaptive_document_router(start_doc_name, start_doc)
            return [pdf_adaptive_document_router], []
        else:
            log.info("not an adaptive_group scan!")
            return [], []

    adaptive_run_router = RunRouter(
        factories=[
            adaptive_document_router_factory
        ]
    )

    live_server(
        manager=adaptive_run_router,
        topics=[args.topics],
        bootstrap_servers=args.bootstrap_servers, 
        group_id=args.group_id
    )
