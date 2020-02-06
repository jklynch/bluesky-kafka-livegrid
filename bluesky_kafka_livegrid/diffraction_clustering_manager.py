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
        self.sample_name_to_total = dict()
        self.sample_name_to_n_sums = dict()
        self.sample_name_to_figure = dict()

        self.data_broker = Broker.named("pdf")

    def __call__(self, name, doc):
        if name == "start":
            start_uid = doc["uid"]
            print(f"got a start document with uid {doc['uid']}")
            #pprint.pprint(doc)
            if "sample_name" not in doc:
                print("no sample name")
                return
            sample_name = doc['sample_name']
            print(f"  sample_name is {sample_name}")
            self.sample_name_to_start_uids[sample_name].append(start_uid)
            self.start_uid_to_sample_name[start_uid] = sample_name
            # do we already have this sample_name?
            if sample_name in self.sample_name_to_data:
                print(f"  we have {sample_name}")
            else:
                print(f"  adding {sample_name}")
                self.sample_name_to_data[sample_name] = list()
                self.sample_name_to_total[sample_name] = np.zeros((2048, 2048))
                self.sample_name_to_n_sums[sample_name] = np.zeros((1000, 2)) #TODO: don't use 1000
                f, ax = plt.subplots()
                self.sample_name_to_figure[sample_name] = (f, ax)
        elif name == "descriptor":
            pass
        elif name == "event":
            pass
        elif name == "stop":
            print("stop:")
            pprint.pprint(doc)
            # hoping the data is all in databroker now
            # get the data!
            start_uid = doc["run_start"]
            if start_uid not in self.start_uid_to_sample_name:
                print(f"did not see the run start for {start_uid}")
                return
            sample_name = self.start_uid_to_sample_name[start_uid]
            print(f"** sample_name: {sample_name}")
            sample_name_uids = self.sample_name_to_start_uids[sample_name]
            print(f"** sample_name_uids:\n{sample_name_uids}")
            sample_count = len(sample_name_uids)
            sample_scan = list(self.data_broker(start_uid))[0]
            diffraction_image = next(sample_scan.data("pe1c_image"))
            print(f"** image shape {diffraction_image.shape}")
            sample_pixel_count = np.product(diffraction_image.shape)
            print(f"** image pixel count {sample_pixel_count}")
            n_diffraction_image = diffraction_image / np.sum(diffraction_image)
            self.sample_name_to_total[sample_name] += n_diffraction_image
            avg_sample_image = self.sample_name_to_total[sample_name] / sample_count
            self.sample_name_to_n_sums[sample_name][sample_count - 1, 1] = (
                np.sum(n_diffraction_image - avg_sample_image)
            )
            

            if sample_count < 2:
                print(f"not enough samples for {sample_name} yet")
            else:
                print(self.sample_name_to_n_sums[sample_name][:sample_count, 1])            
                sample_max = np.max(np.abs(self.sample_name_to_n_sums[sample_name][:sample_count, 1]))
                print(f"sample_max: {sample_max}")
                n_n_sums = self.sample_name_to_n_sums[sample_name][:sample_count, :] / sample_max 
                print(f"normalized sums: {n_n_sums}")
                
                dbscan_clusters = DBSCAN(
                    eps=0.05,
                    min_samples=2
                ).fit(
                    # scikit-learn told me to do this reshape
                    n_n_sums
                )
                cluster_label_set = set(dbscan_clusters.labels_)
                print(f"cluster labels: {dbscan_clusters.labels_}")
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
