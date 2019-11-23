import base64
import datetime
import json
from io import BytesIO

import dash
import dash_core_components as dcc
import dash_html_components as html
import dash_table
from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate
from dramatiq.results.errors import ResultMissing
from PIL import Image

from processimage import process_image

external_stylesheets = ["https://codepen.io/chriddyp/pen/bWLwgP.css"]

app = dash.Dash(__name__, external_stylesheets=external_stylesheets)

app.layout = html.Div(
    [
        html.H1("IsletNet+"),
        dcc.Store(id="memory", data=[]),
        dcc.Interval(id="interval-component", interval=1 * 1000, n_intervals=0),  # in milliseconds
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
                for name, ids in [
                    (["", "Filename"], "filename"),
                    (["", "Status"], "status"),
                    (["Islet", "Count"], "count"),
                    (["Islet", "PlusMinus"], "countplusminus"),
                    (["Islet", "PlusMinusRelative"], "countplusminusrelative"),
                    (["Islet", "Decision"], "countdecision"),
                    (["Volume", "Count"], "volume"),
                    (["Volume", "PlusMinus"], "volumeplusminus"),
                    (["Volume", "PlusMinusRelative"], "volumeplusminusrelative"),
                    (["Volume", "Decision"], "volumedecision"),
                    (["Purity", "Count"], "purity"),
                    (["Purity", "PlusMinus"], "purityplusminus"),
                    (["Purity", "PlusMinusRelative"], "purityplusminusrelative"),
                    (["Purity", "Decision"], "puritydecision"),
                ]
            ],
            data=[],
            editable=False,
            sort_action="native",
            sort_mode="multi",
            row_deletable=True,
            merge_duplicate_headers=True,
        ),
        html.Div(id="output-data-table"),
        html.Div(id="output-image"),
    ]
)


@app.callback(Output("output-image", "children"), [Input("output-datatable", "derived_virtual_data")])
def update_graphs(data):
    if data:
        children = []
        for row in data:
            if row["status"] == "Done":
                children.append(
                    html.Div(
                        [
                            html.H5(row["filename"]),
                            # HTML images accept base64 encoded strings in the same format
                            # that is supplied by the upload
                            html.Img(
                                src="data:image/png;base64," + row["content_resized"], style={"margin": "2px"}
                            ),
                            html.Img(src="data:image/png;base64," + row["mask"], style={"margin": "2px"}),
                            html.Img(src="data:image/png;base64," + row["umap"], style={"margin": "2px"}),
                            html.Hr(),
                        ]
                    )
                )
            else:
                children.append(html.Div([html.H5(row["filename"]), html.Div(row["status"])]))
        return children
    raise PreventUpdate()


@app.callback(
    Output("output-datatable", "data"),
    [Input("interval-component", "n_intervals")],
    [State("output-datatable", "data"), State("memory", "data")],
)
def update_metrics(n, current_data, data):
    new_data = []
    changed = False
    for row in data:
        current_row = None
        for table_row in current_data:
            if table_row["filename"] == row["filename"]:
                current_row = table_row
                break
        if current_row is None:
            current_row = {**row, "status": "Calculating"}

        if current_row["status"].startswith("Calculating"):
            message = process_image.message().copy(message_id=current_row["message_id"])
            try:
                result = message.get_result()
                current_row = {**current_row, **json.loads(result), "status": "Done"}
            except ResultMissing:
                current_row["status"] = current_row["status"] + "."
                if len(current_row["status"]) > 20:
                    current_row["status"] = "Calculating"
            except Exception:
                current_row["status"] = "Error"
            changed = True
        new_data.append(current_row)
    if changed:
        return new_data
    else:
        raise PreventUpdate()


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
    new_content = pil_to_b64(im_pil)
    result = process_image.send(contents)
    return {"content_resized": new_content, "filename": filename, "message_id": result.message_id}


@app.callback(
    Output("memory", "data"),
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
