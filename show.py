import os
from flask import Flask, request, render_template, send_from_directory, abort
import traceback
import glob

app_folder = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__, template_folder=os.path.join(app_folder, 'templates'))

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
        index_pattern = config.get("index_pattern", "*")
        index_pattern = os.path.join(folder, index_pattern)
        prefix, suffix = index_pattern.split('*')
        prefix = len(prefix)
        suffix = len(suffix)
        
        index_list = glob.glob(index_pattern)
        index_list = [f[prefix:-suffix] for f in index_list]
        index_list = sorted(index_list)

        
        if query_index is not None:
            while query_index.startswith(' '):
                query_index = query_index[1:]
            prev_len = len(query_index) + 1
            while prev_len != len(query_index):
                prev_len = len(query_index)
                query_index = query_index.replace(', ', ',')

            query_index_list = list(query_index.split(","))
            index_list = [index for index in query_index_list if index in index_list]

        columns = config.get("columns", [])
        column_heads = ["#"] + [c[0] for c in columns]

        rows = []
        images_per_page = config.get("images_per_page", 20)
        L = images_per_page * (int(page) - 1)
        R = images_per_page * int(page)

        skip_incomplete = config.get("skip_incomplete", False)

        for index in index_list[L:R]:
            row = [(None, index)]
            for column in columns:
                _, column_pattern = column
                if isinstance(column_pattern, str):
                    column_pattern = column_pattern.replace('*', index)
                else:
                    column_pattern = column_pattern(index)

                column_image_candidates = glob.glob(os.path.join(folder, column_pattern))
                # print(column_pattern(index), column_image_candidates)
                if len(column_image_candidates) == 0:
                    column_image = column_pattern
                    if skip_incomplete:
                        row = None
                        break
                else:
                    column_image = column_image_candidates[0]
                row.append((column_image, column_image))

            if row is not None:
                rows.append(row)

        num_pages = (len(index_list) + images_per_page - 1) // images_per_page
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
        )

    
    return render_template('fig_tab.html',
        title=config.get('title', error_msg),   
        **kwargs
    )


@app.route('/file')
def get_image():
    path = request.args.get("path", "None")
    path = os.path.abspath(path)
    try:
        return send_from_directory(os.path.dirname(path), os.path.basename(path))
    except FileNotFoundError:
        abort(404)

if __name__ == '__main__':
    app.run(debug=False, port=8233, host="0.0.0.0") 