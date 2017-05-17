### Running tests with docker image

IMPORTANT: This will copy your public key to allow ssh access from mobile-testkit container to other clusters in the container.
IMPORTANT: If you have been developing on you host machine, you may need `clean.sh` to make sure that the mounted volume does not pick up stale state (.pyc files, test run caches, etc)

In order to pull dependencies needed by `docker/create_cluster.py`, re-run `source setup.sh`:

```
$ source setup.sh
```

Create docker container slaves:

Specifying `--pull` will go and grab the latest docker image builds. 

Specifying `--clean` will do the following:
1. Look for any networks running with the name you passed.
2. Delete containers on that network.
3. Delete the network

If the name is not currently in use on your docker host, a new network will be created without affecting existing networks and containers

```
$ python docker/create_cluster.py --network-name cbl --number-of-nodes 5 --path-to-public-key ~/.ssh/id_rsa.pub --pull --clean
```

Mount local dev environment for iterative development with docker backend. This way you can make changes in your /{user}/mobile-testkit repo and execute within the context of the container.

```
$ docker run --privileged --rm -it --network=cbl --name=mobile-testkit -v $(pwd):/opt/mobile-testkit -v /tmp/pool.json:/opt/mobile-testkit/resources/pool.json -v ~/.ssh/id_rsa:/root/.ssh/id_rsa couchbase/mobile-testkit  /bin/bash
```

And then inside the docker container:

```
# cp ansible.cfg.example ansible.cfg
# sed -i 's/remote_user = vagrant/remote_user = root/' ansible.cfg
# python libraries/utilities/generate_clusters_from_pool.py
# pytest -s --mode=cc --server-version=4.6.1 --sync-gateway-version=1.4.0.2-3 testsuites/syncgateway/functional/tests
```

## Capturing network traffic

From the **Linux Host** where docker is running

```
$ yum install -y tcpdump
$ tcpdump -i docker0 -w /tmp/docker.pcap port 4984
^C
```

Now, get the file to your OSX host and open it in Wireshark.  It should contain all HTTP traffic between the test suite and the sync gateway machines.


## Rebuilding docker image locally

If not up to date on dockerhub, rebuild locally:

```
$ cd docker/mobile-testkit
$ docker build -t mobile-testkit-dev .
```