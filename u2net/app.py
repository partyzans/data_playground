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
        dcc.Store(id="message-ids", data=[]),
        html.H1("IsletNet+"),
        dcc.Interval(id="interval-component", interval=3 * 1000, n_intervals=0),  # in milliseconds
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
            style_data_conditional=[
                {
                    'if': {
                        'column_id': 'countdecision',
                        'filter_query': '{countdecision} eq "check"'
                    },
                    'backgroundColor': 'orange',
                    'color': 'white',
                },
                {
                    'if': {
                        'column_id': 'countdecision',
                        'filter_query': '{countdecision} eq "ok"'
                    },
                    'backgroundColor': 'green',
                    'color': 'white',
                },
                {
                    'if': {
                        'column_id': 'countdecision',
                        'filter_query': '{countdecision} eq "critical"'
                    },
                    'backgroundColor': 'red',
                    'color': 'white',
                },
            ]
        ),
        html.Div(id="output-data-table"),
        html.Div(id="output-image"),
    ]
)


@app.callback(Output("output-image", "children"), [Input("output-datatable", "data")])
def update_graphs(data):
    if data:
        all_statuses = [row["status"] == "Done" for row in data]
        if all(all_statuses):
            children = []
            for row in data:
                message = process_image.message().copy(message_id=row["message_id"])
                result = json.loads(message.get_result())
                children.append(
                    html.Div(
                        [
                            html.H5(row["filename"]),
                            # HTML images accept base64 encoded strings in the same format
                            # that is supplied by the upload
                            html.Img(src="data:image/png;base64," + result["input"], style={"margin": "2px"}),
                            html.Img(src="data:image/png;base64," + result["mask"], style={"margin": "2px"}),
                            html.Img(src="data:image/png;base64," + result["umap"], style={"margin": "2px"}),
                            html.Hr(),
                        ]
                    )
                )
            return children
    raise PreventUpdate()


@app.callback(
    Output("output-datatable", "data"),
    [Input("interval-component", "n_intervals")],
    [State("output-datatable", "data"), State("message-ids", "data")],
)
def new_runner(n, table_data, input_data):
    changed = False
    new_data = []
    for row in table_data:
        if row["status"].startswith("Calculating"):
            message = process_image.message().copy(message_id=row["message_id"])
            try:
                result = message.get_result()
                new_row = {**row, **json.loads(result), "status": "Done"}
                # round decimals
                rount_to = 3
                new_row["countplusminusrelative"] = round(new_row["countplusminusrelative"], rount_to)
                new_row["purity"] = round(new_row["purity"], rount_to)
                new_row["purityplusminus"] = round(new_row["purityplusminus"], rount_to)
                new_row["purityplusminusrelative"] = round(new_row["purityplusminusrelative"], rount_to)
                new_row["volume"] = round(new_row["volume"], rount_to)
                new_row["volumeplusminus"] = round(new_row["volumeplusminus"], rount_to)
                new_row["volumeplusminusrelative"] = round(new_row["volumeplusminusrelative"], rount_to)
                del new_row["mask"]
                del new_row["umap"]
                del new_row["input"]
                changed = True
            except ResultMissing:
                new_row = {**row}
                pass
            except Exception:
                new_row = {**row, "status": "Error"}
                changed = True
            new_data.append(new_row)

        if row["status"].startswith("Done"):
            new_data.append({**row})

        if row["status"].startswith("Error"):
            new_data.append({**row})

    for row in input_data:
        is_new = True
        new_filename = row["filename"]
        for table_row in table_data:
            if table_row["filename"] == new_filename:
                is_new = False
                break
        if is_new:
            new_data.append(row)
            changed = True

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
    print(f"Sending {filename}")
    result = process_image.send(contents)
    return {"filename": filename, "message_id": result.message_id, "status": "Calculating"}


@app.callback(
    Output("message-ids", "data"),
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
    app.run_server(debug=False, host="0.0.0.0")
