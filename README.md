# FigTab
I am introducing a new tool, FigTab, for table of figures generation, developed by me with the help of GPT.

### Functions

- Good-looking visualization of table of figures, with dynamic paging and frozen table title

- Support searching indices for key-cases visualization

- Can be configured easily with a single configuration file for different folders, no explicit/repetitive html generation needed

### Usage
- You can deploy an session by modifying and running show.py, at port `8233` by default.
- Create a config file for your usage cases (see instructions in another section)
- Go to the deployed website, copy the config file path and folder path into the boxes, and press enter
- You can click on the index (eg, `00006`) to copy it
- If would like to search, input to the search index and press enter
  
### Config File Generation
- You need to generate a python file which only contains a python dict, following python grammar. Here is an example with comments (please copy to a code editor for better visualization)
```python
dict(
    # title you want to show on the page
    title="TPD Results - VITON-HD", 
    
    # the way to generate index of the tables
    # using * as the place of index
    # using language of regex, it will list all files matching regex "middle_figure/(.*)_00_person.jpg", and the index will be \1 for all these images
    # the path can be an absolute path, or a relative path w.r.t. the folder you input at the webpage
    index_pattern="middle_figure/*_00_person.jpg", 
    
    # indicate columns in the table
    columns=[
        # choose any one of the styles for each column

        # style 1: simple
        # still uses * in the path, then the actual image path will be the path replacing * with the index
        # e.g., for index 00006, its "Task" image will be middle_figure/00006_00_person.jpg
        ("Task",            "middle_figure/*_00_person.jpg"),
        ("Prompt",          "middle_figure/*_00_prompt.txt"),
        ("Result",          "result/*_00.jpg"),
        ("PoseMap",         "middle_figure/*_00_posemap.jpg"),
        ("DensePose",       "middle_figure/*_00_densepose.jpg"),
        ("BBox",            "middle_figure/*_00_bbox_inpaint.jpg"),
        ("PredictedMask",   "middle_figure/*_00_predicted_mask_inpaint.jpg"),

        # style 2: complicated
        # use a lambda function: index -> filename
        # support using * as regex .*, so that do not have to consider jpg/png, date of experiments, etc.
        ("Task",            lambda k: f"middle_figure/{k}*_person.*"),
        ("Prompt",          lambda k: f"middle_figure/{k}*_prompt.txt"),
        ("Result",          lambda k: f"result/{k}*.*"),
        ("PoseMap",         lambda k: f"middle_figure/{k}*_posemap.*"),
        ("DensePose",       lambda k: f"middle_figure/{k}*_densepose.*"),
        ("BBox",            lambda k: f"middle_figure/{k}*_bbox_inpaint.*"),
        ("PredictedMask",   lambda k: f"middle_figure/{k}*_predicted_mask_inpaint.*"),
       
    ],

    # how many images shown on one page
    images_per_page=10,
)
```
- If the file does not exist, the webpage will show the patterns instead to help you debug
- Updating config file is independent to the website itself, so you do not need to reboot the website after updating config
### Notes
- For the same dataset, you may want to unify the index formats, so that the search can be applied across different methods
- Please only use it for internal development machines, as the code will not check the file permission or injection attacks
