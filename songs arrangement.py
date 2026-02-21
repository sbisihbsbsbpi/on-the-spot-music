import os
import shutil

BASE_DIR = "/Users/tlreddy/Music/OnTheSpot/Tracks"

album_map = {}

# Step 1: Collect all album folders under all artists
for artist in os.listdir(BASE_DIR):
    artist_path = os.path.join(BASE_DIR, artist)
    if not os.path.isdir(artist_path):
        continue

    for album in os.listdir(artist_path):
        album_path = os.path.join(artist_path, album)
        if not os.path.isdir(album_path):
            continue

        album_map.setdefault(album, []).append(album_path)

# Step 2: Move ALL albums to root and merge if needed
for album_name, album_paths in album_map.items():
    target_album_path = os.path.join(BASE_DIR, album_name)
    os.makedirs(target_album_path, exist_ok=True)

    for path in album_paths:
        for file in os.listdir(path):
            src = os.path.join(path, file)
            dst = os.path.join(target_album_path, file)

            # Handle duplicate filenames safely
            if os.path.exists(dst):
                base, ext = os.path.splitext(file)
                i = 1
                while os.path.exists(dst):
                    dst = os.path.join(target_album_path, f"{base}_{i}{ext}")
                    i += 1

            shutil.move(src, dst)

        # Remove empty album folder
        os.rmdir(path)

# Step 3: Remove empty artist folders
for artist in os.listdir(BASE_DIR):
    artist_path = os.path.join(BASE_DIR, artist)
    if os.path.isdir(artist_path) and not os.listdir(artist_path):
        os.rmdir(artist_path)

print("All albums moved to Tracks root and merged successfully.")
