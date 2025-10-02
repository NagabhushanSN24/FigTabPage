import json
import os
import re
from pathlib import Path

from flask import Flask, request, render_template, send_from_directory, abort
import traceback
import glob

app_folder = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__, template_folder=os.path.join(app_folder, 'templates'))

VER = "20251002"


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
        # Sorting: if 'sort' is configured, use metric-based score; else default to alphabetical
        if config.get('sort'):
            columns = config.get('columns', [])
            def _key(item):
                groups = item[1]
                primary = compute_sort_key_for_sample(config, folder, columns, groups)
                secondary = secondary_sort_tuple(config.get('sort', {}), groups)
                return (primary[0], primary[1],) + secondary
            matched_files_data = sorted(matched_files_data, key=_key)
        else:
            matched_files_data = sorted(matched_files_data, key=lambda x: x[0])


        if (not config.get('sort')) and config.get("shuffle", False):
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



# ---- Sorting helpers (metric-based) ----

def _resolve_path_from_ref(config, folder, columns, ref_or_path, groups):
    """
    Resolve a JSON file path either from a column title reference or a direct path template.
    - If ref_or_path is a dict with 'ref', look up the matching column title and use its path.
    - If it has 'path', use that directly.
    Paths may include $1, $2... capture placeholders; we fill them from `groups`.
    Returns an absolute path string.
    """
    path_template = None
    if isinstance(ref_or_path, dict) and 'ref' in ref_or_path:
        ref_name = ref_or_path['ref']
        # columns is a list of tuples: (title, path, [optional json keys list])
        match = None
        for c in columns:
            if len(c) > 0 and c[0] == ref_name:
                match = c
                break
        if match is None:
            raise ValueError(f"Sort config error: ref '{ref_name}' not found in columns")
        path_template = match[1]
    else:
        # assume dict with 'path' or a raw string path template
        path_template = ref_or_path.get('path') if isinstance(ref_or_path, dict) else str(ref_or_path)

    if not path_template:
        raise ValueError("Sort config error: missing 'path' or 'ref'")

    if not path_template.startswith('/'):
        path_template = os.path.join(folder, path_template)

    # Fill $1, $2, ...
    path_filled = format_column(path_template, groups)
    return path_filled


def _read_json_cached(json_cache, path):
    if path in json_cache:
        return json_cache[path]
    with open(path, 'r') as f:
        data = json.load(f)
    json_cache[path] = data
    return data


def _extract_numeric(dct, key):
    """Extract a single numeric value from dict by key (no nesting)."""
    val = dct[key]
    # Allow string numbers
    if isinstance(val, str):
        try:
            val = float(val)
        except:
            pass
    if not isinstance(val, (int, float)):
        raise ValueError(f"Non-numeric value for key '{key}': {val}")
    return float(val)


def _compute_term_value(term, *, config, folder, columns, groups, json_cache):
    metric = term.get('metric', 'abs_diff')
    weight = float(term.get('weight', 1.0))

    def read_desc(desc):
        path = _resolve_path_from_ref(config, folder, columns, desc, groups)
        data = _read_json_cached(json_cache, path)
        key = desc.get('key')
        if key is None:
            raise ValueError("Sort term missing 'key'")
        return _extract_numeric(data, key)

    eps = 1e-12

    if metric in ('abs_diff', 'squared_error', 'diff', 'ratio'):
        gt_desc = term.get('gt')
        pred_desc = term.get('pred')
        if gt_desc is None or pred_desc is None:
            raise ValueError(f"Metric '{metric}' requires 'gt' and 'pred'")
        gt = read_desc(gt_desc)
        pred = read_desc(pred_desc)
        d = pred - gt
        if metric == 'abs_diff':
            v = abs(d)
        elif metric == 'squared_error':
            v = d * d
        elif metric == 'diff':
            v = d
        elif metric == 'ratio':
            v = pred / (abs(gt) + eps)
    elif metric == 'value':
        # Read single descriptor under key 'of' or 'pred'
        desc = term.get('of') or term.get('pred')
        if desc is None:
            raise ValueError("Metric 'value' needs 'of' (or 'pred') descriptor")
        v = read_desc(desc)
    else:
        raise ValueError(f"Unknown metric: {metric}")

    return weight * float(v)


def _aggregate(values, how):
    if not values:
        return float('nan')
    if how == 'sum':
        return sum(values)
    if how == 'mean':
        return sum(values) / len(values)
    if how == 'max':
        return max(values)
    if how == 'min':
        return min(values)
    raise ValueError(f"Unknown aggregate: {how}")


def compute_sort_key_for_sample(config, folder, columns, groups):
    """Return (missing_flag, score) given a sample's capture groups."""
    sort_cfg = config.get('sort')
    if not sort_cfg:
        return (0, 0.0)  # neutral

    aggregate = sort_cfg.get('aggregate', 'sum')
    missing_policy = sort_cfg.get('missing', 'last')
    ascending = bool(sort_cfg.get('ascending', True))
    terms = sort_cfg.get('terms', [])

    json_cache = {}
    values = []
    try:
        for term in terms:
            values.append(_compute_term_value(term, config=config, folder=folder, columns=columns, groups=groups, json_cache=json_cache))
        score = _aggregate(values, aggregate)
        if not ascending:
            score = -score
        return (0, float(score))
    except Exception as e:
        # If missing files or bad keys, handle per policy
        if missing_policy == 'error':
            raise
        # place missing first or last by setting flag
        flag = 1 if missing_policy == 'last' else -1
        # neutral score so only flag dictates position
        return (flag, float('inf') if missing_policy == 'last' else float('-inf'))


def secondary_sort_tuple(sort_cfg, groups):
    tups = []
    for sec in sort_cfg.get('secondary', []):
        # support capture key like "$1"
        key = sec.get('key')
        if key and key.startswith('$'):
            try:
                idx = int(key[1:]) - 1
                tups.append(groups[idx])
            except:
                tups.append('')
        else:
            tups.append('')
    return tuple(tups)

# ---- End sorting helpers ----

if __name__ == '__main__':
    import logging
    app.logger.setLevel(logging.ERROR)
    app.run(debug=False, port=8233, host="0.0.0.0") 