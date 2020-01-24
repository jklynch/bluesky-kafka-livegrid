from bluesky_kafka.kafka import RemoteDispatcher

from bluesky_kafka_livegrid.livegrid_manager import LiveGridManager


def live_server(manager, topics, bootstrap_servers, group_id):
    dispatcher = RemoteDispatcher(
        topics=topics,                          # ["srx-bluesky"],
        bootstrap_servers=bootstrap_servers,    # "10.5.0.18:9092",
        group_id=group_id,                      # "livegrid",
        #deserializer=msgpack.unpackb,
    )

    dispatcher.subscribe(func=manager)

    dispatcher.start()