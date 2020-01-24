import argparse
from collections import defaultdict
import pprint

import matplotlib.pyplot as plt
import numpy as np
from sklearn.cluster import DBSCAN
from sklearn.decomposition import PCA

from bluesky_kafka_livegrid.live_server import live_server
from databroker import Broker


class DiffractionClusteringManager:
    def __init__(self):
        """
        Maintain a dict of sample_name -> data
        """
        self.start_uid_to_sample_name = dict()
        self.sample_name_to_start_uids = defaultdict(list)
        self.sample_name_to_data = dict()
        self.sample_name_to_figure = dict()

        self.data_broker = Broker.named("pdf")

    def __call__(self, name, doc):
        if name == "start":
            start_uid = doc["uid"]
            print(f"got a start document with uid {doc['uid']}")
            sample_name = doc['sample_name']
            print(f"  sample_name is {sample_name}")
            self.sample_name_to_start_uids[sample_name].append(start_uid)
            self.start_uid_to_sample_name[start_uid] = sample_name
            #pprint.pprint(doc)
            # do we already have this sample_name?
            if sample_name in self.sample_name_to_data:
                print(f"  we have {sample_name}")
            else:
                print(f"  adding {sample_name}")
                self.sample_name_to_data[sample_name] = list()
                f, ax = plt.subplots()
                self.sample_name_to_figure[sample_name] = (f, ax)
            #run_start_uid = doc["uid"]
            #self.live_grids[run_start_uid] = LiveGrid(raster_shape=(10, 10), I="det")
            #self.live_grids[run_start_uid].start(doc)
        elif name == "descriptor":
            pass
            #print("descriptor:")
            #pprint.pprint(doc)
            #self.descriptor_uid_to_run_uid[doc["uid"]] = doc["run_start"]
        elif name == "event":
            pass
            #print("event:")
            #pprint.pprint(doc)
            #run_uid = self.descriptor_uid_to_run_uid[doc["descriptor"]]
            #livegrid = self.live_grids[run_uid]
            #livegrid.event(doc)
        elif name == "stop":
            print("stop:")
            pprint.pprint(doc)
            # hoping the data is all in databroker now
            # get the data!
            start_uid = doc["run_start"]
            sample_name = self.start_uid_to_sample_name[start_uid]
            print(f"  sample_name: {sample_name}")
            sample_name_uids = self.sample_name_to_start_uids[sample_name]
            print(f"  sample_name_uids:\n{sample_name_uids}")
            sample_count = len(sample_name_uids)
            if sample_count < 2:
                print(f"not enough samples for {sample_name} yet")
            else:
                sample_pixel_count = 2048*2048   # TODO: get this right
                sample_data_for_clustering = np.zeros((sample_count, sample_pixel_count))
                for sample_i, sample_scan_uid in enumerate(sample_name_uids):
                    # expect diffraction data to be a 2-dimensional array
                    sample_scan = list(self.data_broker(sample_scan_uid))[0]
                    #print(sample_scan.table())
                    # only one image in "pe1c_image"?
                    diffraction_data = next(sample_scan.data("pe1c_image"))
                    sample_data_for_clustering[sample_i, :] = diffraction_data.reshape((-1, ))
                pca = PCA(n_components=min(sample_count, 5))
                pca.fit(sample_data_for_clustering)
                print(f"explained variance: {pca.explained_variance_ratio_}")
                print(f"singular values: {pca.singular_values_}")
                dbscan_clusters = DBSCAN(
                    eps=0.5,
                    min_samples=2
                ).fit(
                    sample_data_for_clustering - pca.components_[0]
                )
                cluster_label_set = set(dbscan_clusters.labels_)
                print(f"\n*** DBSCAN finds {len(cluster_label_set)} cluster(s)\n")
                sample_figure, sample_ax = self.sample_name_to_figure[sample_name]

                # plot a square grid of dots, one dot per sample
                grid_side_length = int(np.ceil(np.sqrt(sample_count)))
                xs = np.zeros(grid_side_length**2)
                ys = np.zeros(grid_side_length**2)
                i = 0
                for y in np.linspace(0, 1, num=grid_side_length, endpoint=False):
                    for x in np.linspace(0, 1, num=grid_side_length, endpoint=False):
                        xs[i] = x
                        ys[i] = y
                        i += 1
                sample_ax.scatter(x=xs[:sample_count], y=ys[:sample_count], c=dbscan_clusters.labels_)
                sample_ax.set_title(sample_name)
                sample_figure.savefig(fname=sample_name, format="pdf")

            #list(db[-1].events(fill=True))[0][‘data’][‘pe1c_image’]
        else:
            print(name)


if __name__ == "__main__":
    argparser = argparse.ArgumentParser()
    argparser.add_argument("--topics")
    argparser.add_argument("--bootstrap-servers")
    argparser.add_argument("--group-id")

    args = argparser.parse_args()
    print(args)

    manager = DiffractionClusteringManager()

    live_server(
        manager=manager,
        topics=[args.topics],
        bootstrap_servers=args.bootstrap_servers, 
        group_id=args.group_id
    )
