dict(
    title="Results",
    index_pattern="*",
    columns=[
        ("Original", "original_*.png"),
        ("Edited", "edited_*.png"),
        ("Ground Truth", "ground_truth_*.png"),
    ],
    images_per_page=20,
)