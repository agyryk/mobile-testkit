import time
from lib.user import User
from lib.admin import Admin
from fixtures import cluster
import pytest


# Scenario-2:
# Single User Single Channel: Create Unique docs and update docs verify all num docs present in changes feed.
# Verify all revisions in changes feed
# https://docs.google.com/spreadsheets/d/1nlba3SsWagDrnAep3rDZHXHIDmRH_FFDeTaYJms_55k/edit#gid=598127796

@pytest.mark.sanity
@pytest.mark.distributed_index
@pytest.mark.parametrize("num_docs", [100])
@pytest.mark.parametrize("num_revisions", [100])
def test_single_user_single_channel_doc_updates(cluster, num_docs, num_revisions):

    start = time.time()
    cluster.reset(config="sync_gateway_default_functional_tests.json")
    num_docs = num_docs
    num_revisions = num_revisions
    username = "User-1"
    password = "password"
    channels = ["channel-1"]

    sgs = cluster.sync_gateways

    admin = Admin(sgs[0])

    single_user = admin.register_user(target=sgs[0], db="db", name=username, password=password, channels=channels)

    # Not using bulk docs
    single_user.add_docs(num_docs)

    assert len(single_user.cache) == num_docs

    # let SG catch up with all the changes
    time.sleep(5)

    single_user.update_docs(num_revisions)

    time.sleep(10)

    doc_name_pattern = "test-"
    status = single_user.verify_all_docs_from_changes_feed(num_revisions, doc_name_pattern)
    assert status

    end = time.time()
    print("TIME:{}s".format(end - start))



