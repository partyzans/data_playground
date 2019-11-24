import hug
import json
import base64
from random import random
from falcon import HTTP_400, HTTP_200, HTTP_202
from PIL import Image

from hug.middleware import CORSMiddleware
import io

from processimage import pil_to_b64, b64_to_pil, process_image

from dramatiq.results import ResultMissing


api = hug.API(__name__)
api.http.add_middleware(CORSMiddleware(api))


results = {}
id_pairs = {}


def writeFile(data, relpath="files/test.png"):
    f = open(relpath, "w+b")
    binary_format = bytearray(data)
    f.write(binary_format)
    f.close()


@hug.startup()
def add_data(api):
    """Adds initial data to the api on startup"""
    print("It's working")


@hug.post("/upload")
def main(request, body, response, debug=True):
    print("Bwah", response)
    print(type(body))
    print(len(body))

    decoded = base64.b64decode(body)
    writeFile(decoded)

    if not body:
        response.status = HTTP_400
    print(request)
    response.status = HTTP_200


@hug.get("/data")
def data(request, body, response, debug=True):
    response.status = HTTP_200

    fake_data = [
        {"id": 1, "name": "iz181207d0_C1V1_2x1000x", "certainty": 123, "img": "img"},
        {"id": 2, "name": "iz181207d0_C1V1_2x1000x", "certainty": 13, "img": "img"},
    ]
    return json.dumps(fake_data)


@hug.get("/submit")
def submit(request, body, response, debug=True):
    response.status = HTTP_200

    im = Image.open("/Users/d_rc/data_playground/sample_data/iz181207d0_C1V1_2x1000x.jpg")
    result = process_image.send(pil_to_b64(im))
    mid = result.message_id
    print(mid)

    results[mid] = result

    return mid


@hug.post("/upload/{cnt}")
def submit(cnt, request, body, response):

    print(cnt)
    print(request)
    # print(body)
    print(response)

    decoded = base64.b64decode(body)
    relpath = "files/" + str(random()) + ".png"
    writeFile(decoded, relpath)

    im = Image.open(relpath)
    result = process_image.send(pil_to_b64(im))
    mid = result.message_id
    results[mid] = result
    id_pairs[mid] = cnt

    response.status = HTTP_200
    return "ok"


@hug.get("/poll")
def poll(request, body, response, debug=True):
    response.status = HTTP_200

    err = False
    resolved_results = []
    for mid, result in results.items():
        try:
            real_result = result.get_result()
            resolved_result = json.loads(real_result)
            resolved_result.pop("umask", None)
            resolved_result.pop("umap", None)
            resolved_result["id"] = mid
            resolved_result["upload_id"] = int(id_pairs[mid])

            resolved_results.append(resolved_result)
        except ResultMissing as e:
            err = True

    if err:
        response.status = HTTP_202
        return "processing"

    # print(resolved_results)
    serialized = json.dumps(resolved_results)
    resolved_results = {}

    return serialized
