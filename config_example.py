dict(
    title="Results",
    index_pattern="test/(*)/(*)/NVIDIA_Warp",
    columns=[
        ("Pattern", "test/$1/$2/NVIDIA_Warp/pattern.png"),
        ("Texture", "test/$1/$2/NVIDIA_Warp/texture.png"),
        ("Video", "test/$1/$2/NVIDIA_Warp/video.mp4"),
        ("Text", "test/$1/$2/NVIDIA_Warp/text.txt"),
        ("Json", "test/$1/$2/NVIDIA_Warp/params.json", ["key1", "key2"] ),  # Shows only key1 and key2 from the json file
    ],
    images_per_page=20,
    image_max_resolution=256,  # Downsample images to this resolution for faster loading (set to None to keep original resolution)
)