import base64
import datetime
from io import BytesIO

import dash
import dash_core_components as dcc
import dash_html_components as html
import dash_table
from dash.dependencies import Input, Output, State
from PIL import Image

from processimage import process_image

external_stylesheets = ["https://codepen.io/chriddyp/pen/bWLwgP.css"]

app = dash.Dash(__name__, external_stylesheets=external_stylesheets)

app.layout = html.Div(
    [
        dcc.Upload(
            id="upload-image",
            children=html.Div(["Drag and Drop or ", html.A("Select Files")]),
            style={
                "width": "100%",
                "height": "60px",
                "lineHeight": "60px",
                "borderWidth": "1px",
                "borderStyle": "dashed",
                "borderRadius": "5px",
                "textAlign": "center",
                "margin": "10px",
            },
            # Allow multiple files to be uploaded
            multiple=True,
        ),
        dash_table.DataTable(
            id="output-datatable",
            columns=[
                {"name": name, "id": ids}
                for name, ids in [("Filename", "filename"), ("Message id", "message_id")]
            ],
            data=[{"filename": "Test", "message_id": "Test"}],
            editable=False,
            sort_action="native",
            sort_mode="multi",
            row_selectable="single",
            row_deletable=True,
        ),
        html.Div(id="output-data-table"),
        html.Div(id="output-image-upload"),
    ]
)


def b64_to_pil(string):
    decoded = base64.b64decode(string)
    buffer = BytesIO(decoded)
    im = Image.open(buffer)

    return im


def pil_to_b64(im, enc_format="png", **kwargs):
    buff = BytesIO()
    im.save(buff, format=enc_format, **kwargs)
    return base64.b64encode(buff.getvalue()).decode("utf-8")


def parse_contents(contents, filename, date):
    im_pil = b64_to_pil(contents.split(";base64,")[-1]).resize((512, 384), Image.LANCZOS).convert("RGB")
    new_content = "data:image/png;base64," + pil_to_b64(im_pil)
    result = process_image.send(contents)
    return {"content_resized": new_content, "filename": filename, "message_id": result.message_id}
    # return html.Div(
    #     [
    #         html.H5(filename),
    #         html.H6(datetime.datetime.fromtimestamp(date)),
    #         # HTML images accept base64 encoded strings in the same format
    #         # that is supplied by the upload
    #         html.Img(src=new_content),
    #         html.Hr(),
    #         html.Div("Raw Content"),
    #         html.Pre(new_content[0:200] + "...", style={"whiteSpace": "pre-wrap", "wordBreak": "break-all"}),
    #         html.Div(result.message_id),
    #     ]
    # )


@app.callback(
    Output("output-datatable", "data"),
    [Input("upload-image", "contents")],
    [State("upload-image", "filename"), State("upload-image", "last_modified")],
)
def update_output(list_of_contents, list_of_names, list_of_dates):
    if list_of_contents is not None:
        children = [
            parse_contents(c, n, d) for c, n, d in zip(list_of_contents, list_of_names, list_of_dates)
        ]
        return children
    return []


if __name__ == "__main__":
    app.run_server(debug=True)
