class AppID:
    VideoSplitter = 1
    FaceRecogniser = 2
    XGBoostGridSearch = 3
    ImagesMerger = 4


app_name_to_id = {
    'video_splitter': AppID.VideoSplitter,
    'face_recogniser': AppID.FaceRecogniser,
    'xgb_grid_search': AppID.XGBoostGridSearch,
    'images_merger': AppID.ImagesMerger,
}
