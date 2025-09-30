import json
import os
import re
from pathlib import Path

from flask import Flask, request, render_template, send_from_directory, abort
import traceback
import glob

app_folder = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__, template_folder=os.path.join(app_folder, 'templates'))

VER = "20250930"


def match_files(folder, index_pattern):
    # Remove parenthesis used for capture groups
    index_pattern_glob = index_pattern.replace('(', '').replace(')', '')
    index_pattern_regex = index_pattern.replace('*', '.+')
    matched_files = Path(folder).glob(index_pattern_glob)
    matcher = re.compile(index_pattern_regex)
    matched_files_data = []
    for matched_file in matched_files:
        match = matcher.match(matched_file.relative_to(folder).as_posix())
        if match:
            matched_files_data.append((matched_file.as_posix(), match.groups()))
    return matched_files_data

def format_column(value, groups):
    """Replace {$X} placeholders with matched regex groups"""
    for i, group in enumerate(groups):
        value = value.replace(f'${i+1}', group)
    return value

@app.route('/')
def index():
    config_file = request.args.get("config", "None")
    folder = request.args.get("folder", "None")
    page = request.args.get("page", 1)

    if page == "":
        page = 1
    page = int(page)

    config_file = os.path.expanduser(config_file)
    folder = os.path.expanduser(folder)

    error_msg = ""

    query_index = request.args.get("query_index", None)
    if query_index == '':
        query_index = None

    try:
        with open(config_file) as f:
            code = compile(f.read(), '', 'eval')
            config = eval(code)
    except Exception as e:
        config = {}
        error_msg = f"Error: Config file {config_file} cannot be read"
        traceback.print_exc()
   
    # print(config)

    kwargs = dict(
        config_file=config_file,
        folder=folder, 
        last_query_index=query_index
    )

    if len(config) > 0:
        matched_files_data = match_files(folder, config['index_pattern'])
        matched_files_data = sorted(matched_files_data, key=lambda x: x[0])

        if config.get("shuffle", False):
            import hashlib
            matched_files_data = sorted(matched_files_data, key=lambda x: int(hashlib.md5(x[0].encode()).hexdigest(), 16))
        
        if query_index is not None:
            # TODO SNB: handle this
            while query_index.startswith(' '):
                query_index = query_index[1:]
            prev_len = len(query_index) + 1
            while prev_len != len(query_index):
                prev_len = len(query_index)
                query_index = query_index.replace(', ', ',')

            query_index_list = list(query_index.split(","))
            filtered_files_data = []
            for matched_file_data in matched_files_data:
                matched_file_index = '/'.join(matched_file_data[1])
                for query_index in query_index_list:
                    if query_index in matched_file_index:
                        filtered_files_data.append(matched_file_data)
                        break
            matched_files_data = filtered_files_data

        columns = config.get("columns", [])
        column_heads = ["#"] + [c[0] for c in columns]

        rows = []
        images_per_page = config.get("images_per_page", 20)
        L = images_per_page * (int(page) - 1)
        R = images_per_page * int(page)
        skip_incomplete = config.get("skip_incomplete", False)

        for matched_file_data in matched_files_data[L:R]:
            row = [(None, '/'.join(matched_file_data[1]))]
            for column in columns:
                column_pattern = column[1]
                if not column_pattern.startswith("/"):
                    column_pattern = os.path.join(folder, column_pattern)
                column_pattern = format_column(column_pattern, matched_file_data[1])

                column_image_candidates = glob.glob(os.path.join(folder, column_pattern))
                # print(column_pattern(index), column_image_candidates)
                if len(column_image_candidates) == 0:
                    column_image = column_pattern
                    if skip_incomplete:
                        row = None
                        break
                else:
                    column_image = column_image_candidates[0]

                contents = column_image
                if Path(column_image).suffix in ['.txt']:
                    try:
                        with open(column_image) as f:
                            contents = "\n".join(f.readlines())
                    except:
                        contents = f"Error: File {column_image} cannot be read"
                elif Path(column_image).suffix in ['.json']:
                    try:
                        with open(column_image) as f:
                            json_data = json.load(f)
                        keys = column[2] if len(column) >= 3 else list(json_data.keys())
                        filtered_json_data = {k: json_data[k] for k in keys if k in json_data}
                        contents = json.dumps(filtered_json_data, indent=4)
                    except:
                        contents = f"Error: File {column_image} cannot be read"
                else:
                    from urllib.parse import quote
                    contents = quote(contents, encoding='utf-8')

                row.append((contents, column_image))

            if row is not None:
                rows.append(row)

        num_pages = (len(matched_files_data) + images_per_page - 1) // images_per_page
        page = max(page, 1)
        page = min(page, num_pages)
        navi = []
        prev_page = int(page) - 1
        next_page = int(page) + 1

        def url_at_page(p):
            return f"?config={config_file}&folder={folder}&page={p}"
        
        prev_page = None if prev_page < 1 else url_at_page(prev_page)
        next_page = None if next_page > num_pages else url_at_page(next_page)

        page_rad = 5

        if page - page_rad > 1:
            navi.append((
                1,
                url_at_page(1)
            ))

        if page - page_rad > 2:
            navi.append((
                "...",
                "..."
            ))

        for page_index in range(page - page_rad, page + page_rad + 1):
            if 1 <= page_index <= num_pages:
                navi.append((
                    page_index,
                    url_at_page(page_index) 
                ))

        if page + page_rad < num_pages - 1:
            navi.append((
                "...",
                "..."
            ))

        if page + page_rad < num_pages:
            navi.append((
                num_pages,
                url_at_page(num_pages)
            ))

        kwargs = dict(
            config_file=config_file,
            folder=folder,   
            column_heads=column_heads,
            rows=rows,
            page=page,
            prev_page=prev_page,
            next_page=next_page,
            navi=navi,
            error=error_msg != "",
            last_query_index=query_index,
            img_max_width=config.get("img_max_width", 1024),
            img_max_height=config.get("img_max_height", 256),
            image_max_resolution=config.get("image_max_resolution", None),
        )

    
    return render_template('fig_tab.html',
        title=config.get('title', error_msg),   
        ver=VER,
        **kwargs
    )


@app.route('/file')
def get_image():
    """Serve files. If `max_side` is provided and the file is an image, serve a downsampled, cached version.
    Query params:
      - path: absolute or relative file path
      - max_side: optional integer; if provided and >0, images are resized so the longer side == max_side
    """
    from PIL import Image, ImageOps
    import io
    import mimetypes
    import pathlib
    import hashlib
    import time

    path = request.args.get("path", "None")
    max_side = request.args.get("max_side", None)
    # Normalize and secure path
    path = os.path.abspath(path)
    try:
        # If no resizing requested, just send the original
        if not max_side or str(max_side).lower() == "none":
            return send_from_directory(os.path.dirname(path), os.path.basename(path))
        try:
            max_side = int(max_side)
        except Exception:
            max_side = None
        if not max_side or max_side <= 0:
            return send_from_directory(os.path.dirname(path), os.path.basename(path))

        # Only handle common image types
        ext = os.path.splitext(path)[1].lower()
        image_exts = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff"}
        if ext not in image_exts:
            return send_from_directory(os.path.dirname(path), os.path.basename(path))

        # Build a cache path that invalidates when source mtime changes
        src_mtime = int(os.path.getmtime(path))
        cache_root = os.path.join(app_folder, ".cache_images")
        os.makedirs(cache_root, exist_ok=True)

        # -- Cache policy: cleanup before use --
        # 1) Delete files older than 10 days
        # 2) Enforce 10 GiB soft cap by deleting oldest files first
        TEN_DAYS_SEC = 10 * 24 * 60 * 60
        SIZE_CAP_BYTES = 10 * 1024 * 1024 * 1024  # 10 GiB
        now = time.time()

        # Time-based cleanup and initial listing
        total_size = 0
        entries = []
        try:
            with os.scandir(cache_root) as it:
                for de in it:
                    if not de.is_file():
                        continue
                    try:
                        st = de.stat()
                        if (now - st.st_mtime) > TEN_DAYS_SEC:
                            try:
                                os.remove(de.path)
                            except OSError:
                                pass
                        else:
                            entries.append((de.path, st.st_size, st.st_mtime))
                            total_size += st.st_size
                    except OSError:
                        pass
        except FileNotFoundError:
            pass

        # Size-cap cleanup (oldest first)
        if total_size > SIZE_CAP_BYTES:
            entries.sort(key=lambda x: x[2])  # by mtime asc
            i = 0
            while total_size > SIZE_CAP_BYTES and i < len(entries):
                p, sz, _ = entries[i]
                try:
                    os.remove(p)
                    total_size -= sz
                except OSError:
                    pass
                i += 1

        # hash by absolute path + mtime + max_side to avoid collisions
        cache_key = hashlib.sha256((path + f"|{src_mtime}|{max_side}").encode("utf-8")).hexdigest()[:24]
        cache_name = f"{cache_key}_{max_side}{ext}"
        cache_path = os.path.join(cache_root, cache_name)

        if os.path.exists(cache_path):
            return send_from_directory(cache_root, cache_name)

        # Load and downsample with EXIF orientation handled
        with Image.open(path) as im:
            im = ImageOps.exif_transpose(im)
            w, h = im.size
            longer = max(w, h)
            if longer <= max_side:
                # No need to resize: cache original bytes to speed up future requests
                im.save(cache_path)
                return send_from_directory(cache_root, cache_name)
            scale = max_side / float(longer)
            new_w = max(1, int(round(w * scale)))
            new_h = max(1, int(round(h * scale)))
            # Use high-quality downsampling
            im = im.resize((new_w, new_h), Image.Resampling.LANCZOS)

            save_kwargs = {}
            if ext in {".jpg", ".jpeg"}:
                # Reasonable quality to reduce size
                save_kwargs.update(dict(quality=88, optimize=True, progressive=True))
            elif ext == ".png":
                save_kwargs.update(dict(optimize=True))
            elif ext == ".webp":
                save_kwargs.update(dict(quality=88, method=4))

            im.save(cache_path, **save_kwargs)

        return send_from_directory(cache_root, cache_name)
    except FileNotFoundError:
        abort(404)

if __name__ == '__main__':
    import logging
    app.logger.setLevel(logging.ERROR)
    app.run(debug=False, port=8233, host="0.0.0.0") 