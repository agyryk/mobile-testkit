import time
from lib.admin import Admin
import pytest

from cluster_setup import cluster

@pytest.mark.sanity
def test_1(cluster):

    cluster.reset("sync_gateway_default.json")

    start = time.time()
    sgs = cluster.sync_gateways

    admin = Admin(sgs[0])
    admin.register_user(target=sgs[0], db="db", name="seth", password="password", channels=["ABC", "CBS", "NBC", "FOX"])
    admin.register_user(target=sgs[0], db="db", name="admin", password="password", channels=["*"])

    users = admin.get_users()

    seth = users["seth"]
    admin = users["admin"]

    # Round robin
    count = 1
    num_sgs = len(cluster.sync_gateways)
    while count <= 20:
        seth.add_docs(100, uuid_names=True, bulk=True)
        seth.target = cluster.sync_gateways[count % num_sgs]
        count += 1

    assert len(seth.cache) == 2000

    print(seth)

    time.sleep(10)

    seth_cache_ids = seth.cache.keys()
    seth.verify_ids_from_changes(seth_cache_ids)

    end = time.time()
    print("TIME:{}s".format(end - start))

