import base64
import json
from io import BytesIO

import dramatiq
import numpy as np
import torch
import torch.nn as nn
from dramatiq.brokers.redis import RedisBroker
from dramatiq.results.backends import RedisBackend
from dramatiq.results import Results
from PIL import Image

from model import UNet

result_backend = RedisBackend()
redis_broker = RedisBroker(host="127.0.0.1", port=6379)
redis_broker.add_middleware(Results(backend=result_backend))
dramatiq.set_broker(redis_broker)
device = "cpu"


def load_model(model_path, device):
    model = UNet(3, 3)
    model.load_state_dict(torch.load(model_path, map_location=torch.device(device)))
    return model


def b64_to_pil(string):
    decoded = base64.b64decode(string)
    buffer = BytesIO(decoded)
    return Image.open(buffer)


def pil_to_b64(im, enc_format="png", **kwargs):
    buff = BytesIO()
    im.save(buff, format=enc_format, **kwargs)
    return base64.b64encode(buff.getvalue()).decode("utf-8")


def prepare_image(image, out_size, mean, device):
    input_image = image.resize(out_size, Image.LANCZOS).convert("RGB")
    input_array = np.array(input_image, dtype=np.float32)
    prepared_tensor = (
        ((torch.from_numpy(input_array) - torch.tensor(mean)) / 255.0).permute(2, 0, 1).unsqueeze(0)
    )
    return prepared_tensor.to(device)


def postprocess_model(result, islet_threshold, exo_threshold) -> np.array:
    classes = result.argmax(axis=0).astype("uint8")
    final: np.array = np.zeros_like(classes)
    sure_islets = result[2, :, :] > islet_threshold
    final[(classes == 2) & sure_islets] = 255
    final[(classes == 2) & ~sure_islets] = 128
    sure_exo = result[1, :, :] > exo_threshold
    final[(classes == 1) & sure_exo] = 128
    return final


@dramatiq.actor(store_results=True)
def process_image(image):
    print(f"Starting with data: {image[:100]}")
    with torch.no_grad():
        pil_image = b64_to_pil(image.split(";base64,")[-1])
        prepared = prepare_image(pil_image, (512, 384), (69.2614, 55.9220, 32.6043), device)
        model = load_model("./models/unet_W512_H384_3_final.pth", device)
        model_result = model.forward(prepared)
        probab = nn.Softmax(dim=0).forward(model_result[0])
        post_processed = postprocess_model(probab.cpu().numpy(), 0.0, 0.0)
        post_processed_image = Image.fromarray(post_processed, mode="L")
        base64_result = pil_to_b64(post_processed_image)
        print(f"Finished with data: {image[:100]}")
        return json.dumps({"mask": base64_result})
