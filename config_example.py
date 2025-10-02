dict(
    title="Results",
    index_pattern="test/(*)/(*)/NVIDIA_Warp",
    columns=[
        ("Pattern", "test/$1/$2/NVIDIA_Warp/pattern.png"),
        ("Texture", "test/$1/$2/NVIDIA_Warp/texture.png"),
        ("Video", "test/$1/$2/NVIDIA_Warp/video.mp4"),
        ("Text", "test/$1/$2/NVIDIA_Warp/text.txt"),
        ("Json", "test/$1/$2/NVIDIA_Warp/params.json", ["key1", "key2"]),  # Shows only key1 and key2 from the json file
    ],
    images_per_page=20,
    image_max_resolution=256,  # Downsample images to this resolution for faster loading (set to None to keep original resolution)
    # Downsample images to this resolution for faster loading (set to None to keep original resolution)
    sort={
        "ascending": True,  # default True
        "aggregate": "sum",  # sum | mean | max | min
        "terms": [
            {
                "metric": "abs_diff",  # value | diff | abs_diff | squared_error | ratio
                "gt": {"ref": "GT Measurements", "key": "pant_length"},  # or {"path": "...", "key": "..."}
                "pred": {"ref": "Ours3 Measurements", "key": "pant_length"},
                "weight": 1.0  # optional
            },
            # add more terms/measurements/models with weights if you wish
        ],
        "secondary": [
            {"type": "alphanumeric", "key": "$1"},  # optional tie-breakers (e.g., capture groups)
        ],
        "missing": "last"  # first | last | error
    },
)
