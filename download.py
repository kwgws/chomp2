from datetime import datetime
import json
import os
import uuid
import wget

import dateparser
import regex as re
import requests

_SEARCH_URL = "https://archive.org/advancedsearch.php?q=collection:{collection}&fl[]=identifier&rows=999999&output=json"
_re_fulldate = re.compile(r"(19[6-9]\d|20[0-1]\d)-[0-1]\d")
_re_yearonly = re.compile(r"19[6-9]\d|20[0-1]\d")


def error(txt):
    with open("error.log", "a", encoding="utf-8") as f:
        f.write(f"[{datetime.now().isoformat()}] {txt}\n")
    log("ERROR: " + txt)


def log(txt):
    with open("download.log", "a", encoding="utf-8") as f:
        f.write(f"[{datetime.now().isoformat()}] {txt}\n")
    print(txt)


def get_items(in_path, out_path):

    # Parse collections.
    print("Loading collections...")
    collections = set()

    for file in [f for f in os.listdir(in_path) if f.endswith(".txt")]:
        with open(os.path.join(in_path, file), "r", encoding="utf-8") as f:
            for line in f.readlines():
                collections.add(line.strip())

    collections = list(collections)
    collections.sort()

    log(f"Loaded {len(collections)} total collections.")

    # Scrape items from within collections.
    print("\nRequesting items...")
    i = 0

    for collection in collections:

        collection_path = os.path.join(out_path, collection + ".txt")
        if os.path.exists(collection_path):
            log(f"Skipping {collection}, items already discovered.")
            continue

        search_url = _SEARCH_URL.format(collection=collection)
        items = set()

        log(f"Getting items from {collection}...")
        try:
            r = requests.get(search_url)
            data = r.json()
        except Exception:
            error(f"Could not parse collection: {collection}.")
            continue

        for item in data["response"]["docs"]:
            items.add(item["identifier"])
            i = i + 1

        items = list(items)
        items.sort()

        if len(items) == 0:
            error(f"No items found in collection: {collection}, skipping.")
            continue

        with open(collection_path, "w", encoding="utf-8") as f:
            f.write("\n".join(items))

    log(f"Found {i} new items.\n")


def get_metadata(in_path, out_path):

    # Parse items.
    print("Loading items...")
    collections = []
    i = 0

    for file in [f for f in os.listdir(in_path) if f.endswith(".txt")]:

        collection = dict(identifier=file[:-4], items=[])

        with open(os.path.join(in_path, file), "r", encoding="utf-8") as f:
            for line in f.readlines():
                collection["items"].append(line.strip())
                i = i + 1

        collections.append(collection)

    log(f"Loaded {i} total items.")

    # Scrape text files from within items.
    print("\nRequesting text files...")
    i = 0

    for collection in collections:
        for item in collection["items"]:

            item_path = os.path.join(out_path, item + ".json")
            if os.path.exists(item_path):
                log(f"Skipping {item}, metadata already discovered.")
                continue

            log(f"Getting metadata from {item}...")
            meta_url = f"https://archive.org/metadata/{item}"
            try:
                r = requests.get(meta_url)
                data = r.json()
            except Exception:
                error(f"Could not parse item: {item}.")
                continue

            metadata = dict(
                id=str(uuid.uuid5(uuid.NAMESPACE_DNS, data["metadata"]["identifier"])),
                identifier=data["metadata"]["identifier"],
                collection=collection["identifier"],
                title=data["metadata"].get("title", "no-title"),
                date=data["metadata"].get("date", "no-date"),
                language=data["metadata"].get("language", "no-language"),
                tags=data["metadata"].get("subject", []),
                files=[],
            )

            for file in data["files"]:
                if file["name"].endswith(".txt") or file["name"].endswith(".pdf"):
                    if file["format"] == "Metadata":
                        continue
                    metadata["files"].append(
                        dict(
                            id=str(uuid.uuid5(uuid.NAMESPACE_DNS, file["name"])),
                            name=file["name"],
                            format=file["format"],
                            url=f"https://archive.org/download/{item}/{file['name']}",
                            size=file["size"],
                            md5=file["md5"],
                            crc32=file["crc32"],
                            sha1=file["sha1"],
                        )
                    )
            if len(metadata["files"]) == 0:
                error(f"No files found in item: {item}, skipping.")
                continue

            with open(item_path, "w", encoding="utf-8") as f:
                f.write(json.dumps(metadata, sort_keys=True, indent=4))
            i = i + 1

    log(f"Found new metadata for {i} items.\n")


def get_txt(in_path, out_path):

    files = []
    i = 1

    for metafile in [f for f in os.listdir(in_path) if f.endswith(".json")]:
        with open(os.path.join(in_path, metafile), "r", encoding="utf-8") as f:
            data = json.loads(f.read())

        # Check Date
        date = None
        try:
            date = dateparser.parse(data["date"], settings=dict(REQUIRE_PARTS=["month", "year"]))
            date = date.strftime("%Y-%m")
        except Exception:
            pass

        for file in [f for f in data["files"] if f["format"] == "DjVuTXT"]:

            # A handful of files have path names boiled in somehow.
            name = file["name"].split("/")[-1].split("\\")[-1]

            # Save UUID in filename.
            name = name[:-4] + " - " + file["id"] + name[-4:]

            if not date:
                try:
                    date = _re_fulldate.search(data["name"]).group(0)
                    date = date.strftime("%Y-%m")
                except Exception:
                    continue

            if date is not None:
                name = date + " - " + name

            files.append(dict(
                name=name,
                url=file["url"],
            ))

            print(f"Loading metadata...{i}", end="\r")
            i = i + 1
    print()

    i = 0
    for file in files:

        if os.path.exists(os.path.join(out_path, file["name"])):
            log(f"Skipping {file['name']}, already downloaded.")
            continue

        try:
            log(f"Downloading {file['url']}...")
            newfile = wget.download(file["url"])
        except Exception:
            error(f"Could not get file: {file['url']}.")
            continue
        print()
        i = i + 1

        os.rename(newfile, os.path.join(out_path, file["name"]))
    log(f"Downloaded {i} files.\n")


if __name__ == "__main__":

    #get_items("collections", "items")
    #get_metadata("items", "metadata")
    get_txt("metadata", "corpus")

    log("DONE!\n")
