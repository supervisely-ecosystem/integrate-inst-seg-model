import os
import cv2
from dotenv import load_dotenv
import supervisely as sly

from detectron2 import model_zoo
from detectron2.engine import DefaultPredictor
from detectron2.config import get_cfg
from detectron2.data import MetadataCatalog

load_dotenv("local.env")
load_dotenv(os.path.expanduser("~/supervisely.env"))

# code for detectron2 inference copied from official COLAB tutorial (inference section):
# https://colab.research.google.com/drive/16jcaJoc6bCFAQ96jDe2HwtXj7BMD_-m5


class MyModel(sly.nn.inference.InstanceSegmentation):
    def __init__(self, model_dir: str = None):
        super().__init__(model_dir)

        # Initialize Detectron2 model from config
        cfg = get_cfg()
        cfg.merge_from_file(
            model_zoo.get_config_file(
                "COCO-InstanceSegmentation/mask_rcnn_R_50_FPN_3x.yaml"
            )
        )
        # cfg.MODEL.ROI_HEADS.SCORE_THRESH_TEST = 0.5
        cfg.MODEL.DEVICE = "cpu"
        cfg.MODEL.WEIGHTS = os.path.join(model_dir, "model_weights.pkl")

        self.predictor = DefaultPredictor(cfg)
        self.class_names = MetadataCatalog.get(cfg.DATASETS.TRAIN[0]).get(
            "thing_classes"
        )
        print("model has been successfully deployed")

    def get_classes(self) -> list[str]:
        return self.class_names  # ["cat", "dog", ...]

    def predict(
        self, image_path: str, confidence_threshold: float = 0.8
    ) -> list[sly.nn.PredictionMask]:
        image = cv2.imread(image_path)  # BGR

        # get predictions from Detectron2 model
        outputs = self.predictor(image)
        pred_classes = outputs["instances"].pred_classes.detach().numpy()
        pred_class_names = [self.class_names[pred_class] for pred_class in pred_classes]
        pred_scores = outputs["instances"].scores.detach().numpy().tolist()
        pred_masks = outputs["instances"].pred_masks.detach().numpy()

        results = []
        for score, class_name, mask in zip(pred_scores, pred_class_names, pred_masks):
            if score >= confidence_threshold:
                results.append(sly.nn.PredictionMask(class_name, mask, score))
        return results


if sly.is_production():
    # code below is running on Supervisely platform in production
    m = MyModel()
    m.serve()
else:
    # # advanced debug for Supervisely Team
    # team_id = int(os.environ["context.teamId"])
    # sly.app.development.connect_to_supervisely_vpn_network()
    # sly.app.development.create_debug_task(team_id, port="8000")
    # exit(0)

    # for local development and debugging
    model_dir = "./my_model"
    m = MyModel(model_dir)

    image_path = "./demo_data/image_01.jpg"
    results = m.predict(image_path)
    vis_path = "./demo_data/image_01_prediction.jpg"
    m.visualize(results, image_path, vis_path)
    print("predictions and visualization have been created")
