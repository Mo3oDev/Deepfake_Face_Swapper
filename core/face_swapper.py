import cv2
import numpy as np
import insightface
from insightface.app import FaceAnalysis

class FaceSwapper:
    def __init__(self, det_size=(640, 640), ctx_id=0, model_path='models/face_swapper_model.onnx'):
        """
        model_path: Ruta al modelo ONNX de face swapper a utilizar. Debe ser configurada según el modelo disponible.
        """
        self.app = FaceAnalysis(name='buffalo_l')
        self.app.prepare(ctx_id=ctx_id, det_size=det_size)
        self.swapper = insightface.model_zoo.get_model(model_path)

    def detect_faces(self, img_path):
        img = cv2.imread(img_path)
        faces = self.app.get(img)
        faces = sorted(faces, key=lambda x: x.bbox[0])
        return img, faces

    def swap_faces(self, target_img_path, source_img_path, output_path):
        img, faces = self.detect_faces(target_img_path)
        if len(faces) == 0:
            raise RuntimeError(f"No se detectaron caras en {target_img_path}")
        source_img, source_faces = self.detect_faces(source_img_path)
        if len(source_faces) == 0:
            raise RuntimeError(f"No se detectaron caras en {source_img_path}")
        source_face = source_faces[0]
        res = img.copy()
        for face in faces:
            res = self.swapper.get(res, face, source_face, paste_back=True)
        cv2.imwrite(output_path, res)
        return output_path, res
