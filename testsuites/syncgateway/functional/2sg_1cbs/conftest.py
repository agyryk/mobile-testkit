import pytest
import os

from keywords.utils import log_info
from keywords.ClusterKeywords import ClusterKeywords
from keywords.constants import SYNC_GATEWAY_CONFIGS


# This will be called once for the first test in the test session.
# After all the tests have completed in the directory
# the function will execute everything after the yield
@pytest.fixture(scope="module")
def setup_2sg_1cbs_suite(request):
    log_info("Setting up 'setup_2sg_1cbs_suite' ...")

    server_version = request.config.getoption("--server-version")
    sync_gateway_version = request.config.getoption("--sync-gateway-version")

    # Set the CLUSTER_CONFIG environment variable to 2sg_1cbs
    cluster_helper = ClusterKeywords()
    cluster_helper.set_cluster_config("2sg_1cbs")

    cluster_helper.provision_cluster(
        cluster_config=os.environ["CLUSTER_CONFIG"],
        server_version=server_version,
        sync_gateway_version=sync_gateway_version,
        sync_gateway_config="{}/sync_gateway_default_functional_tests_di.json".format(SYNC_GATEWAY_CONFIGS)
    )

    yield

    cluster_helper.unset_cluster_config()

    log_info("Tearing down 'setup_2sg_1cbs_suite' ...")