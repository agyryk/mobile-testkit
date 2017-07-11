from couchbase.bucket import Bucket
from requests import Session
from requests.exceptions import HTTPError
import time
import random

from concurrent.futures import ProcessPoolExecutor
from concurrent.futures import as_completed

from keywords.SyncGateway import sync_gateway_config_path_for_mode
from keywords import couchbaseserver
from keywords import document
from libraries.testkit.cluster import Cluster
from keywords.MobileRestClient import MobileRestClient
from keywords.ClusterKeywords import ClusterKeywords
from keywords.SyncGateway import SyncGateway
from keywords.utils import log_info


# Set the default value to 404 - view not created yet
SG_VIEWS = {
    'sync_gateway_access': ["access"],
    'sync_gateway_access_vbseq': ["access_vbseq"],
    'sync_gateway_channels': ["channels"],
    'sync_gateway_role_access': ["role_access"],
    'sync_gateway_role_access_vbseq': ["role_access_vbseq"],
    'sync_housekeeping': [
        "all_bits",
        "all_docs",
        "import",
        "old_revs",
        "principals",
        "sessions",
        "tombstones"
    ]
}


def test_system_test(params_from_base_test_setup):
 
    cluster_config = params_from_base_test_setup['cluster_config']
    mode = params_from_base_test_setup['mode']

    # Scenario parameters
    server_seed_docs = int(params_from_base_test_setup['server_seed_docs'])
    max_docs = int(params_from_base_test_setup['max_docs'])
    num_users = int(params_from_base_test_setup['num_users'])

    # Create paramters
    create_batch_size = int(params_from_base_test_setup['create_batch_size'])
    create_delay = float(params_from_base_test_setup['create_delay'])

    # Update parameters
    update_runtime_sec = int(params_from_base_test_setup['update_runtime_sec'])
    update_batch_size = int(params_from_base_test_setup['update_batch_size'])
    update_delay = float(params_from_base_test_setup['update_delay'])

    log_info('Running System Test #1')
    log_info('> server_seed_docs   = {}'.format(server_seed_docs))
    log_info('> max_docs           = {}'.format(max_docs))
    log_info('> create_batch_size  = {}'.format(create_batch_size))
    log_info('> create_delay       = {}'.format(create_delay))
    log_info('> update_batch_size  = {}'.format(update_batch_size))
    log_info('> update_delay       = {}'.format(update_delay))
    log_info('> update_runtime_sec = {}'.format(update_runtime_sec))
    log_info('> num_users          = {}'.format(num_users))

    # Validate

    # Number of docs should be equally divisible by number of users
    if max_docs % num_users != 0:
        raise ValueError('max_docs must be devisible by number_of_users')

    # Number of docs per user (max_docs / num_users) should be equally
    # divisible by the batch size for easier computation
    docs_per_user = max_docs / num_users
    if docs_per_user % create_batch_size != 0:
        raise ValueError('docs_per_user ({}) must be devisible by create_batch_size ({})'.format(
            docs_per_user,
            create_batch_size
        ))

    if num_users < update_batch_size or update_batch_size < 1:
        raise ValueError("'update_batch_size' should be greater than one or less than or equal to the number of users")

    sg_conf_name = 'sync_gateway_default'
    sg_conf = sync_gateway_config_path_for_mode(sg_conf_name, mode)

    # Reset cluster state
    c = Cluster(config=cluster_config)
    c.reset(sg_config_path=sg_conf)

    cluster_helper = ClusterKeywords()
    topology = cluster_helper.get_cluster_topology(cluster_config)

    cbs_url = topology['couchbase_servers'][0]
    cbs_admin_url = cbs_url.replace('8091', '8092')
    cb_server = couchbaseserver.CouchbaseServer(cbs_url)
    bucket_name = cb_server.get_bucket_names()[0]
    cbs_ip = cb_server.host

    headers = {'Content-Type': 'application/json'}
    cbs_session = Session()
    cbs_session.headers = headers
    cbs_session.auth = ('Administrator', 'password')

    log_info('Seeding {} with {} docs'.format(cbs_ip, server_seed_docs))
    sdk_client = Bucket('couchbase://{}/{}'.format(cbs_ip, bucket_name), password='password', timeout=300)
    sg_client = MobileRestClient()

    # Stop SG before loading the server
    sg_url = topology['sync_gateways'][0]['public']
    sg_admin_url = topology['sync_gateways'][0]['admin']
    sg_db = 'db'
    #sg_util = SyncGateway()
    #sg_util.stop_sync_gateway(cluster_config=cluster_config, url=sg_url)

    # Scenario Actions
    # delete_views(cbs_session, cbs_admin_url, bucket_name)
    # load_bucket(sdk_client, server_seed_docs)
    # start_sync_gateway(cluster_config, sg_util, sg_url, mode)
    # wait_for_view_creation(cbs_session, cbs_admin_url, bucket_name)

    # Start concurrent creation of docs (max docs / num users)
    # Each user will add batch_size number of docs via bulk docs and sleep for 'create_delay'
    # Once a user has added number of expected docs 'docs_per_user', it will terminate.
    users = create_docs(
        sg_admin_url=sg_admin_url,
        sg_url=sg_url,
        sg_db=sg_db,
        num_users=num_users,
        number_docs_per_user=docs_per_user,
        batch_size=create_batch_size,
        create_delay=create_delay
    )
    assert len(users) == num_users

    # Start concurrent updates of update
    # Update batch size is the number of users that will concurrently update all of their docs
    update_docs(
        sg_admin_url=sg_admin_url,
        sg_url=sg_url,
        sg_db=sg_db,
        users=users,
        update_runtime_sec=update_runtime_sec,
        batch_size=update_batch_size,
        update_delay=update_delay
    )


def start_normal_changes_worker():
    pass


def start_longpoll_changes_worker():
    pass


def start_continuous_changes_worker():
    pass


def add_user_docs(client, sg_url, sg_db, user_name, user_auth, number_docs_per_user, batch_size, create_delay):

    doc_ids = []
    docs_pushed = 0
    batch_count = 0
    
    while docs_pushed < number_docs_per_user:

        # Create batch of docs
        docs = document.create_docs(
            doc_id_prefix='{}_{}'.format(user_name, batch_count),
            number=batch_size,
            prop_generator=document.doc_1k,
            channels=[user_name]
        )

        # Add batch of docs
        log_info('User ({}) adding {} docs.'.format(user_name, number_docs_per_user))
        docs = client.add_bulk_docs(sg_url, sg_db, docs, auth=user_auth)
        batch_doc_ids = [doc['id'] for doc in docs]
        doc_ids.extend(batch_doc_ids)

        docs_pushed += batch_size
        batch_count += 1
        # Sleep 'create_delay' second before adding another batch
        time.sleep(create_delay)

    return doc_ids


def create_users_add_docs_task(user_number,
                               sg_admin_url,
                               sg_url,
                               sg_db,
                               number_docs_per_user,
                               batch_size,
                               create_delay):

    sg_client = MobileRestClient()

    user_name = 'st_user_{}'.format(user_number)
    user_pass = 'password'

    # Create user
    sg_client.create_user(
        url=sg_admin_url,
        db=sg_db,
        name=user_name,
        password=user_pass,
        channels=[user_name]
    )

    # Create session
    user_auth = sg_client.create_session(
        url=sg_admin_url,
        db=sg_db,
        name=user_name, password=user_pass
    )

    # Start bulk doc creation
    doc_ids = add_user_docs(
        client=sg_client,
        sg_url=sg_url,
        sg_db=sg_db,
        user_name=user_name,
        user_auth=user_auth,
        number_docs_per_user=number_docs_per_user,
        batch_size=batch_size,
        create_delay=create_delay
    )

    return user_name, user_auth, doc_ids


def create_docs(sg_admin_url, sg_url, sg_db, num_users, number_docs_per_user, batch_size, create_delay):
    """ Concurrent creation of docs """

    users = {}

    start = time.time()
    log_info('Starting {} users to add {} docs per user'.format(num_users, number_docs_per_user))

    with ProcessPoolExecutor(max_workers=num_users) as pe:

        # Start concurrent create block
        futures = [pe.submit(
            create_users_add_docs_task,
            user_number=i,
            sg_admin_url=sg_admin_url,
            sg_url=sg_url,
            sg_db=sg_db,
            number_docs_per_user=number_docs_per_user,
            batch_size=batch_size,
            create_delay=create_delay
        ) for i in range(num_users)]

        # Block until all futures are completed or return
        # exception in future.result()
        for future in as_completed(futures):
            username, auth, doc_ids = future.result()
            log_info('User ({}) done adding docs.'.format(username))

            # Add user to global dictionary
            users[username] = {
                'auth': auth,
                'doc_ids': doc_ids,
                'updates': 0
            }

    end = time.time() - start
    log_info('Doc creation of {} docs per user and delay: {}s took -> {}s'.format(
        number_docs_per_user, create_delay, end
    ))

    return users


def update_docs_task(users, user_index, sg_url, sg_db):

    user_name = 'st_user_{}'.format(user_index)

    # Get a random value to determin the update method
    # ~ 90% ops bulk, 10% ops single
    rand = random.random()
    if rand <= 0.90:
        update_method = 'bulk_docs'
    else:
        update_method = 'put'

    sg_client = MobileRestClient()

    # Get a random user
    random_user_auth = users[user_name]['auth']
    random_user_doc_ids = users[user_name]['doc_ids']

    log_info('Updating {} docs, method ({}) number of updates: {} ({})'.format(
        len(random_user_doc_ids),
        update_method,
        users[user_name]['updates'],
        user_name
    ))

    # Update the user's docs
    if update_method == 'bulk_docs':
        # Get docs for that user
        user_docs, errors = sg_client.get_bulk_docs(url=sg_url, db=sg_db, doc_ids=random_user_doc_ids, auth=random_user_auth)
        assert len(errors) == 0

        # Update the 'updates' property
        for doc in user_docs:
            doc['updates'] += 1

        # Add the docs via build_docs
        sg_client.add_bulk_docs(url=sg_url, db=sg_db, docs=user_docs, auth=random_user_auth)

    else:

        # Do a single GET / PUT for each of the user docs
        for doc_id in random_user_doc_ids:
            doc = sg_client.get_doc(url=sg_url, db=sg_db, doc_id=doc_id, auth=random_user_auth)
            doc['updates'] += 1
            sg_client.put_doc(url=sg_url, db=sg_db, doc_id=doc_id, doc_body=doc, rev=doc['_rev'], auth=random_user_auth)

    return user_name


def update_docs(sg_admin_url, sg_url, sg_db, users, update_runtime_sec, batch_size, update_delay):

    log_info('Starting updates with batch size (concurrent users updating): {} and delay: {}s'.format(
        batch_size,
        update_delay
    ))
    log_info('Continue to update for {}s'.format(update_runtime_sec))

    num_users = len(users)
    start = time.time()
    continue_updating = True
    current_user_index = 0

    while continue_updating:

        elapsed_sec = time.time() - start
        log_info('Updaing for: {}s'.format(elapsed_sec))
        if elapsed_sec > update_runtime_sec:
            log_info('Runtime limit reached. Exiting ...')
            break

        with ProcessPoolExecutor(max_workers=batch_size) as pe:

            # Start concurrent update block
            futures = [pe.submit(
                update_docs_task,
                users,
                current_user_index + i,
                sg_url,
                sg_db
            ) for i in range(batch_size)]
            
            # Block until all futures are completed or return
            # exception in future.result()
            for future in as_completed(futures):
                # Increment updates
                user = future.result()
                users[user]['updates'] += 1
                log_info('Completed updates ({})'.format(user))

        current_user_index = (current_user_index + batch_size) % num_users
        time.sleep(update_delay)


def delete_views(cbs_session, cbs_admin_url, bucket_name):
    """ Deletes all SG Views from Couchbase Server
    """

    # Delete the SG views before seeding the server
    # We want to see how long does it take for SG views to get created
    for view in SG_VIEWS:
        log_info('Deleting view: {}'.format(view))
        try:
            resp = cbs_session.delete('{}/{}/_design/{}'.format(cbs_admin_url, bucket_name, view))
            resp.raise_for_status()
        except HTTPError:
            if resp.status_code == 404:
                log_info('View already deleted: {}'.format(view))
            else:
                raise


def load_bucket(sdk_client, server_seed_docs):
    # Seed the server with server_seed_docs number of docs
    docs = {'doc_{}'.format(i): {'foo': 'bar'} for i in range(server_seed_docs)}
    sdk_client.upsert_multi(docs)


def start_sync_gateway(cluster_config, sg_util, sg_url, mode):
    # Start SG
    sg_util.start_sync_gateway(cluster_config=cluster_config, url=sg_url, config=sg_conf)
    # It takes a couple of seconds for the view indexing to begin
    time.sleep(5)


def wait_for_view_creation(cbs_session, cbs_admin_url, bucket_name):
    # Wait for the views to be ready
    # TODO: Add this to couchbase_server.py
    start = time.time()
    for view in SG_VIEWS:
        for index in SG_VIEWS[view]:
            log_info('Waiting for view {}/{} to be finished'.format(view, index))
            resp = cbs_session.get('{}/{}/_design/{}/_view/{}?stale=false'.format(cbs_admin_url, bucket_name, view, index))
            resp.raise_for_status()
    end = time.time()
    log_info('Views creation took {} seconds'.format(end - start))