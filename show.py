import os
from flask import Flask, request, render_template, send_from_directory, abort

app_folder = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__, template_folder=os.path.join(app_folder, 'templates'))

@app.route('/')
def index():
    config_file = request.args.get("config", "None")
    folder = request.args.get("folder", "None")
    page = int(request.args.get("page", 1))

    config_file = os.path.expanduser(config_file)
    folder = os.path.expanduser(folder)

    error_msg = ""

    try:
        with open(config_file) as f:
            code = compile(f.read(), '', 'eval')
            config = eval(code)
    except:
        config = {}
        error_msg = f"Error: Config file {config_file} not found"
   
    # print(config)

    kwargs = {}

    if len(config) > 0:
        import glob
        index_pattern = config.get("index_pattern", "*")
        index_pattern = os.path.join(folder, index_pattern)
        prefix, suffix = index_pattern.split('*')
        prefix = len(prefix)
        suffix = len(suffix)
        
        index_list = glob.glob(index_pattern)
        index_list = [f[prefix:-suffix] for f in index_list]
        index_list = sorted(index_list)

        columns = config.get("columns", [])
        column_heads = ["#"] + [c[0] for c in columns]

        rows = []
        images_per_page = config.get("images_per_page", 20)
        L = images_per_page * (int(page) - 1)
        R = images_per_page * int(page)

        for index in index_list[L:R]:
            row = [(None, index)]
            for column in columns:
                _, column_pattern = column
                column_image = os.path.join(folder, column_pattern.replace('*', index))
                row.append((column_image, column_image))
            rows.append(row)

        num_pages = (len(index_list) + images_per_page - 1) // images_per_page
        navi = []
        prev_page = int(page) - 1
        next_page = int(page) + 1

        def url_at_page(p):
            return f"?config={config_file}&folder={folder}&page={p}"
        
        prev_page = None if prev_page < 1 else url_at_page(prev_page)
        next_page = None if next_page > num_pages else url_at_page(next_page)

        if page - 10 > 1:
            navi.append((
                1,
                url_at_page(1)
            ))

        if page - 10 > 2:
            navi.append((
                "...",
                "..."
            ))

        for page_index in range(page - 10, page + 10 + 1):
            if 1 <= page_index <= num_pages:
                navi.append((
                    page_index,
                    url_at_page(page_index) 
                ))

        if page + 10 < num_pages - 1:
            navi.append((
                "...",
                "..."
            ))

        if page + 10 < num_pages:
            navi.append((
                num_pages,
                url_at_page(num_pages)
            ))

        kwargs = dict(
            folder=folder,   
            column_heads=column_heads,
            rows=rows,
            page=page,
            prev_page=prev_page,
            next_page=next_page,
            navi=navi,
            error=error_msg != ""
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
    app.run(debug=False, port=8233, ) 