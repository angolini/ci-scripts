import argparse
import json
import os.path

from helpers import status
from apps.docker_store import DockerStore
from apps.compose_apps import ComposeApps


def get_args():
    parser = argparse.ArgumentParser("Parse docker store and obtain layers metadata of all Apps' images")
    parser.add_argument("-d", "--docker-data-root",
                        help="Path to the docker data root", default="/var/lib/docker")
    parser.add_argument("-a", "--apps-root", help="Path to the compose apps root dir", default="./")
    parser.add_argument("-t", "--tag", help="Expected tag of images")
    parser.add_argument("-o", "--out-file", help="Json file to ouput the gathered layers metadata to")
    a = parser.parse_args()
    return a


def print_layer_details(layer: DockerStore.Layer):
    title2value = {
        "DiffID": layer.diff_id,
        "ChainID": layer.chain_id,
        "CacheID": layer.cache_id,
        "DataPath": layer.data_path,
        "Size": layer.size,
        "Usage": layer.usage,
        "UsageWithMeta": layer.usage_with_meta,
        "TarMetaSize": layer.tar_split_size,
        "Overall Usage": layer.overall_usage
    }
    for t, v in title2value.items():
        status(f"{' ':<16}{t:<16}{v}", prefix="")


if __name__ == '__main__':
    args = get_args()
    status(f"Parsing the docker store {args.docker_data_root}...")
    docker_store = DockerStore(args.docker_data_root)
    status(f"The docker store has been parsed; fs block size is {docker_store.fs_block_size}")

    status("Processing metadata about each App layer...")
    apps = ComposeApps(args.apps_root, quiet=True)
    apps_layers_meta = {
        "fs_block_size": docker_store.fs_block_size,
        "layers": {}
    }
    for app in apps:
        status(f"Processing App metadata: {app.name}", prefix="=== ")
        for img in app.images(expand_env=True):
            img_uri = img
            if img_uri.startswith("hub.foundries.io"):
                img_uri += ":" + args.tag

            image = docker_store.images_by_ref.get(img_uri)
            if not image:
                status("Image metadata are not found in local store; "
                       f"`SKIP_ARCHS` must be set for the image: {img_uri}", prefix="==== ")
                continue

            status(f"Image: {img_uri}", prefix="==== ")
            for layer in image.layers:
                if layer.digest in apps_layers_meta["layers"]:
                    status(f"Layer has been already processed: {layer.digest}", prefix="\t=====")
                    continue
                status(f"Layer: {layer.digest}", prefix="\t=====")
                apps_layers_meta["layers"][layer.digest] = {
                    "size": layer.size,
                    "usage": layer.overall_usage
                }
                print_layer_details(layer)
                status("\n", prefix="")
            status("Image processing done", prefix="==== ")

        status(f"App metadata has been successfully processed: {app.name}\n", prefix="=== ")

    status(f"Storing App layers metadata; file: {args.out_file}", prefix="=== ")
    with open(args.out_file, "+w") as f:
        json.dump(apps_layers_meta, f)

    status("Processing metadata about each App layer has been successfully completed")