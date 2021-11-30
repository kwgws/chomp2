def load_collections(collections_file):

    collections = []

    try:
        with open(collections_file, "r", encoding="utf-8") as f:
            for line in f.readlines():
                collections.append(line.strip())
    except FileNotFoundError:
        print("WRN: No collections file found.")
        pass

    if len(collections) == 0:
        print("ERR: No collections specified!")

    return collections
