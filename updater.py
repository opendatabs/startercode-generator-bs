# IMPORTS -------------------------------------------------------------------- #

import glob
import json
import os
import re
import warnings
from datetime import datetime

import pandas as pd
import requests
from tqdm import tqdm

warnings.simplefilter(action="ignore", category=FutureWarning)


# CONSTANTS ------------------------------------------------------------------ #

PATH_METADATA = "_metadata_json/"
BASELINK_DATASHOP = "https://data.bs.ch/explore/dataset/"

PROVIDER = "Statistisches Amt des Kantons Basel-Stadt - DCC Data Competence Center"
SHOP_METADATA_LINK = (
    "https://data.bs.ch/api/explore/v2.1/catalog/datasets/100057/exports/json"
)
DATASET_API = "https://data.bs.ch/api/explore/v2.1/catalog/datasets/{identifier}"
CONTACT = "Open Data Basel-Stadt | opendata@bs.ch"

GITHUB_ACCOUNT = "opendatabs"
REPO_NAME = "startercode-opendatabs"
REPO_BRANCH = "main"
REPO_R_MARKDOWN_OUTPUT = "01_r-markdown/"
REPO_R_NOTEBOOK_OUTPUT = "02_r-notebook/"
REPO_PYTHON_OUTPUT = "03_python/"
REPO_MARIMO_OUTPUT = "04_marimo/"
TEMP_PREFIX = "_work/"

TEMPLATE_FOLDER = "_templates/"
TEMPLATE_HEADER = "template_header.md"
TEMPLATE_PYTHON = "template_python.ipynb"
TEMPLATE_RMARKDOWN = "template_rmarkdown.Rmd"
TEMPLATE_RNOTEBOOK = "template_rnotebook.ipynb"
TEMPLATE_MARIMO = "template_marimo.py"

# canonical code shared across templates (see _templates/shared/)
SHARED_FOLDER = "_templates/shared/"
SHARED_GET_DATASET_PY = "get_dataset.py"
SHARED_GET_DATASET_R = "get_dataset.R"
SHARED_ANALYZE_DATA_PY = "analyze_data.py"
SHARED_ANALYZE_DATA_R = "analyze_data.R"

TODAY_DATE = datetime.today().strftime("%Y-%m-%d")
TODAY_DATETIME = datetime.today().strftime("%Y-%m-%d %H:%M:%S")

# max length of dataset title in markdown table
TITLE_MAX_CHARS = 200

# don't prune an output folder if the live catalogue has fewer than this fraction
# of the files currently on disk there — a drop that large is more likely a bad/
# incomplete API response than real dataset removals
PRUNE_MIN_RATIO = 0.5

# select metadata features that are going to be displayed in starter code files
KEYS_DATASET = [
    "dataset_identifier",
    "title",
    "description",
    "contact_name",
    "issued",
    "modified",
    "rights",
    "temporal_coverage_start_date",
    "temporal_coverage_end_date",
    "themes",
    "keywords",
    "creator",
    "reference",
]


# FUNCTIONS ------------------------------------------------------------------ #
def get_current_json():
    """Request metadata catalogue from data shop"""
    res = requests.get(SHOP_METADATA_LINK)
    # # save with date to allow for later error and change analysis
    # with open(f"{PATH_METADATA}{TODAY_DATE}.json", "wb") as file:
    # file.write(res.content)
    data = json.loads(res.text)
    return pd.DataFrame(data)


def sort_data(data):
    """Sort by integer prefix of identifier"""
    data["id_short"] = data.dataset_identifier.apply(lambda x: x.split("@")[0]).astype(int)
    data.sort_values("id_short", inplace=True)
    data.reset_index(drop=True, inplace=True)
    return data


def prune_stale_files(data):
    """Remove generated files for datasets no longer in the live catalogue.

    Skips pruning a folder if the live dataset count has dropped too far below
    the number of files already on disk there, since a drop that large is more
    likely a bad/incomplete API response than genuine dataset removals.
    """
    valid_identifiers = set(data["dataset_identifier"])

    output_dirs = [
        (f"{TEMP_PREFIX}{REPO_R_MARKDOWN_OUTPUT}", ".Rmd"),
        (f"{TEMP_PREFIX}{REPO_R_NOTEBOOK_OUTPUT}", ".ipynb"),
        (f"{TEMP_PREFIX}{REPO_PYTHON_OUTPUT}", ".ipynb"),
        (f"{TEMP_PREFIX}{REPO_MARIMO_OUTPUT}", ".py"),
    ]

    for out_dir, ext in output_dirs:
        existing = glob.glob(f"{out_dir}*{ext}")
        if not existing:
            continue

        if len(valid_identifiers) < len(existing) * PRUNE_MIN_RATIO:
            print(
                f"WARNING: skipping prune for {out_dir} — live catalogue has "
                f"{len(valid_identifiers)} datasets but {len(existing)} files exist there. "
                "This drop looks too large to be real removals; likely a bad API response."
            )
            continue

        removed = 0
        for path in existing:
            identifier = os.path.splitext(os.path.basename(path))[0]
            if identifier not in valid_identifiers:
                os.remove(path)
                removed += 1
        if removed:
            print(f"Pruned {removed} stale file(s) from {out_dir}")


def prepare_data_for_codebooks(data):
    """Prepare metadata from catalogue in order to create code files"""
    data["metadata"] = None

    # iterate over all datasets and compose refined data for markdown and code cells
    for idx in tqdm(data.index):
        md = [f"- **{k.capitalize()}** `{data.loc[idx, k]}`\n" for k in KEYS_DATASET]
        data.loc[idx, "metadata"] = "".join(md)

    return data


def json_escape(text):
    """Escape text for safe embedding inside a JSON string literal (handles backslashes, quotes, control chars)"""
    return json.dumps(text)[1:-1]


def load_shared_source(filename):
    """Read a canonical code snippet shared across multiple templates"""
    with open(f"{SHARED_FOLDER}{filename}", encoding="utf-8") as file:
        return file.read().rstrip("\n")


def indent_block(text, spaces):
    """Indent every line of a multi-line code block by a fixed amount.

    Used when splicing a flush-left shared snippet into an indented context
    (e.g. inside a marimo cell function) — indenting only the first line and
    leaving continuation lines flush-left breaks Python syntax and, for
    markdown, gets misparsed as an indented code block (see the DATASET_FIELDS
    rendering bug this same issue caused).
    """
    prefix = " " * spaces
    return "\n".join(prefix + line if line else line for line in text.split("\n"))


def splice_indented_placeholder(text, placeholder, content, spaces=4):
    """Replace a `{{ PLACEHOLDER }}` placeholder's WHOLE line (any leading
    whitespace) with `content`, indented uniformly to `spaces`.

    Replacing only the token (not the whole line) leaves the template's own
    leading whitespace attached to the spliced block's first line while every
    other line stays flush-left — mixed indentation that breaks Python syntax
    (see the GET_DATASET_PY_MARIMO bug this caused). The placeholder must sit
    alone on its own line in the template.
    """
    pattern = r"^[ \t]*\{\{ " + re.escape(placeholder) + r" \}\}[ \t]*$"
    return re.sub(pattern, lambda _: indent_block(content, spaces), text, flags=re.MULTILINE)


def load_shared_sections(filename):
    """Parse a shared snippet file into named sections, delimited by
    '# === SECTION: name ===' marker comments, for selective per-placeholder splicing.
    """
    text = load_shared_source(filename)
    parts = re.split(r"^#\s*=== SECTION: (\w+) ===\s*$\n", text, flags=re.MULTILINE)
    return {parts[i]: parts[i + 1].strip("\n") for i in range(1, len(parts), 2)}


def splice_sections(text, sections, prefix, escape=False):
    """Replace `{{ PREFIX_SECTION_NAME }}` placeholders (flush-left, e.g. inside
    a Jupyter cell or plain-text template) with their named section bodies.
    """
    for name, body in sections.items():
        placeholder = "{{ " + f"{prefix}{name.upper()}" + " }}"
        text = text.replace(placeholder, json_escape(body) if escape else body)
    return text


def splice_indented_sections(text, sections, prefix, spaces=4):
    """Like splice_sections, but for placeholders that sit on their own indented
    line inside a code block (e.g. a marimo cell) — see splice_indented_placeholder.
    """
    for name, body in sections.items():
        text = splice_indented_placeholder(text, f"{prefix}{name.upper()}", body, spaces)
    return text


def get_dataset_fields(identifier):
    """Request field schema (name, type, description) for a single dataset"""
    url = DATASET_API.format(identifier=identifier)
    try:
        res = requests.get(url, timeout=10)
        res.raise_for_status()
        fields = res.json().get("fields", [])
    except (requests.RequestException, ValueError):
        return []

    return [
        {
            "name": f.get("name", ""),
            "type": f.get("type", ""),
            "description": "; ".join(
                " ".join(line.split())
                for line in re.split(r"\r\n|\r|\n", f.get("description") or f.get("description_de") or "")
                if line.strip()
            ),
        }
        for f in fields
    ]


def format_fields_markdown(fields):
    """Render a field schema as a markdown table"""
    if not fields:
        return "_No field information available._\n"

    rows = ["| Field | Type | Description |\n", "| :-- | :-- | :-- |\n"]
    for f in fields:
        description = f["description"] or "—"
        rows.append(f"| `{f['name']}` | {f['type']} | {description} |\n")
    return "".join(rows)


def fetch_dataset_fields(data):
    """Fetch and format the field schema for every dataset"""
    data["fields_markdown"] = None
    for idx in tqdm(data.index):
        identifier = data.loc[idx, "dataset_identifier"]
        fields = get_dataset_fields(identifier)
        data.loc[idx, "fields_markdown"] = format_fields_markdown(fields)
    return data


def create_python_notebooks(data):
    """Create Jupyter Notebooks with Python starter code"""
    for idx in tqdm(data.index):
        with open(f"{TEMPLATE_FOLDER}{TEMPLATE_PYTHON}") as file:
            py_nb = file.read()

        # populate template with metadata
        identifier = data.loc[idx, "dataset_identifier"]
        py_nb = py_nb.replace("{{ PROVIDER }}", PROVIDER)
        py_nb = py_nb.replace(
            "{{ DATASET_TITLE }}", re.sub('"', "'", data.loc[idx, "title"])
        )

        py_nb = py_nb.replace(
            "{{ DATASET_DESCRIPTION }}", re.sub('"', "'", data.loc[idx, "description"])
        )
        py_nb = py_nb.replace("{{ DATASET_IDENTIFIER }}", identifier)
        py_nb = py_nb.replace(
            "{{ DATASET_METADATA }}", re.sub('"', "'", data.loc[idx, "metadata"])
        )
        py_nb = py_nb.replace(
            "{{ DATASET_FIELDS }}", json_escape(data.loc[idx, "fields_markdown"])
        )
        py_nb = py_nb.replace("{{ GET_DATASET_PY }}", json_escape(GET_DATASET_PY_SOURCE))
        py_nb = splice_sections(py_nb, EDA_PY_SECTIONS, "EDA_", escape=True)

        ds_link = (
            f"[Direct data shop link for dataset]({BASELINK_DATASHOP}{identifier})"
        )
        py_nb = py_nb.replace("{{ DATASHOP_LINK }}", ds_link)

        code_block = f"df = get_dataset('{identifier}')"
        py_nb = py_nb.replace("{{LOAD_DATA}}", code_block)

        py_nb = py_nb.replace("{{ CONTACT }}", CONTACT)

        # to properly populate the code cell for data set import
        # we need to operate on the actual JSON rather than use simple string replacement
        py_nb = json.loads(py_nb, strict=False)

        # save to disk
        with open(f"{TEMP_PREFIX}{REPO_PYTHON_OUTPUT}{identifier}.ipynb", "w") as file:
            file.write(json.dumps(py_nb))


def create_rmarkdown(data):
    """Create R Markdown files with R starter code"""
    for idx in tqdm(data.index):
        with open(f"{TEMPLATE_FOLDER}{TEMPLATE_RMARKDOWN}") as file:
            rmd = file.read()

        # populate template with metadata
        identifier = data.loc[idx, "dataset_identifier"]
        rmd = rmd.replace("{{ GET_DATASET_R }}", GET_DATASET_R_SOURCE)
        rmd = splice_sections(rmd, EDA_R_SECTIONS, "EDA_")
        rmd = rmd.replace("{{ DATASET_TITLE }}", data.loc[idx, "title"])
        rmd = rmd.replace("{{ PROVIDER }}", PROVIDER)
        rmd = rmd.replace("{{ TODAY_DATE }}", TODAY_DATE)
        rmd = rmd.replace("{{ DATASET_IDENTIFIER }}", identifier)
        rmd = rmd.replace("{{ DATASET_DESCRIPTION }}", data.loc[idx, "description"])
        rmd = rmd.replace("{{ DATASET_METADATA }}", data.loc[idx, "metadata"])
        rmd = rmd.replace("{{ DATASET_FIELDS }}", data.loc[idx, "fields_markdown"])

        ds_link = (
            f"[Direct data shop link for dataset]({BASELINK_DATASHOP}{identifier})"
        )
        rmd = rmd.replace("{{ DATASHOP_LINK }}", ds_link)

        download_link = f"{BASELINK_DATASHOP}{identifier}/download?format=csv&timezone=Europe%2FZurich"
        code_block = f"df <- get_dataset('{download_link}')"
        rmd = rmd.replace("{{ LOAD_DATA }}", code_block)

        rmd = rmd.replace("{{ CONTACT }}", CONTACT)

        # save to disk
        with open(
            f"{TEMP_PREFIX}{REPO_R_MARKDOWN_OUTPUT}{identifier}.Rmd",
            "w",
            encoding="utf-8",
        ) as file:
            file.write("".join(rmd))


def create_rnotebooks(data):
    """Create Jupyter Notebooks with R starter code"""
    for idx in tqdm(data.index):
        with open(f"{TEMPLATE_FOLDER}{TEMPLATE_RNOTEBOOK}") as file:
            r_nb = file.read()

        # populate template with metadata
        identifier = data.loc[idx, "dataset_identifier"]
        r_nb = r_nb.replace("{{ GET_DATASET_R }}", json_escape(GET_DATASET_R_SOURCE))
        r_nb = splice_sections(r_nb, EDA_R_SECTIONS, "EDA_", escape=True)
        r_nb = r_nb.replace("{{ PROVIDER }}", PROVIDER)
        r_nb = r_nb.replace(
            "{{ DATASET_TITLE }}", re.sub('"', "'", data.loc[idx, "title"])
        )

        r_nb = r_nb.replace(
            "{{ DATASET_DESCRIPTION }}", re.sub('"', "'", data.loc[idx, "description"])
        )
        r_nb = r_nb.replace("{{ DATASET_IDENTIFIER }}", identifier)
        r_nb = r_nb.replace(
            "{{ DATASET_METADATA }}", re.sub('"', "'", data.loc[idx, "metadata"])
        )
        r_nb = r_nb.replace(
            "{{ DATASET_FIELDS }}", json_escape(data.loc[idx, "fields_markdown"])
        )
        r_nb = r_nb.replace("{{ TODAY_DATE }}", TODAY_DATE)
        ds_link = (
            f"[Direct data shop link for dataset]({BASELINK_DATASHOP}{identifier})"
        )
        r_nb = r_nb.replace("{{ DATASHOP_LINK }}", ds_link)

        download_link = f"{BASELINK_DATASHOP}{identifier}/download"
        code_block = f"df = get_dataset('{download_link}')"
        r_nb = r_nb.replace("{{ LOAD_DATA }}", code_block)

        r_nb = r_nb.replace("{{ CONTACT }}", CONTACT)

        # to properly populate the code cell for data set import
        # we need to operate on the actual JSON rather than use simple string replacement
        r_nb = json.loads(r_nb, strict=False)

        # save to disk
        with open(
            f"{TEMP_PREFIX}{REPO_R_NOTEBOOK_OUTPUT}{identifier}.ipynb", "w"
        ) as file:
            file.write(json.dumps(r_nb))


def create_marimo_apps(data):
    """Create marimo apps (.py) in 04_marimo/ using template_marimo.py placeholders."""
    template_path = f"{TEMPLATE_FOLDER}{TEMPLATE_MARIMO}"
    with open(template_path, "r", encoding="utf-8") as f:
        template = f.read()

    for idx in tqdm(data.index):
        identifier = data.loc[idx, "dataset_identifier"]

        filled = template

        filled = filled.replace("{{ PROVIDER }}", PROVIDER)
        filled = filled.replace("{{ DATASET_IDENTIFIER }}", identifier)
        filled = filled.replace("{{ DATASET_TITLE }}", data.loc[idx, "title"])
        filled = filled.replace("{{ DATASET_DESCRIPTION }}", data.loc[idx, "description"])
        filled = filled.replace("{{ CONTACT }}", CONTACT)

        ds_link = f"{BASELINK_DATASHOP}{identifier}"
        filled = filled.replace("{{ DATASHOP_LINK }}", ds_link)

        filled = filled.replace("{{ DATASET_METADATA }}", data.loc[idx, "metadata"])
        filled = filled.replace("{{ DATASET_FIELDS }}", data.loc[idx, "fields_markdown"])
        filled = splice_indented_placeholder(filled, "GET_DATASET_PY_MARIMO", GET_DATASET_PY_SOURCE)
        filled = splice_indented_sections(filled, EDA_PY_SECTIONS, "EDA_")

        out_path = f"{TEMP_PREFIX}{REPO_MARIMO_OUTPUT}{identifier}.py"
        with open(out_path, "w", encoding="utf-8") as f_out:
            f_out.write(filled)


def get_header(dataset_count):
    """Retrieve header template and populate with date and count of data records"""
    with open(f"{TEMPLATE_FOLDER}{TEMPLATE_HEADER}", encoding="utf-8") as file:
        header = file.read()
    header = re.sub("{{ DATASET_COUNT }}", str(int(dataset_count)), header)
    header = re.sub("{{ TODAY_DATE }}", TODAY_DATETIME, header)
    return header


def create_overview(data, header):
    """Create README with link table"""
    baselink_r_gh = f"https://github.com/{GITHUB_ACCOUNT}/{REPO_NAME}/blob/{REPO_BRANCH}/{REPO_R_MARKDOWN_OUTPUT}"
    baselink_py_gh = f"https://github.com/{GITHUB_ACCOUNT}/{REPO_NAME}/blob/{REPO_BRANCH}/{REPO_PYTHON_OUTPUT}"
    baselink_py_colab = f"https://githubtocolab.com/{GITHUB_ACCOUNT}/{REPO_NAME}/blob/{REPO_BRANCH}/{REPO_PYTHON_OUTPUT}"
    baselink_r_colab = f"https://githubtocolab.com/{GITHUB_ACCOUNT}/{REPO_NAME}/blob/{REPO_BRANCH}/{REPO_R_NOTEBOOK_OUTPUT}"
    baselink_py_marimo = f"https://{GITHUB_ACCOUNT}.github.io/{REPO_NAME}/marimo/"

    renku_base_url = f"https://renkulab.io/p/dcc-bs/{REPO_NAME}"
    binder_base_url = (
        f"https://mybinder.org/v2/gh/{GITHUB_ACCOUNT}/{REPO_NAME}/{REPO_BRANCH}"
    )
    binder_lab_link = f"{binder_base_url}?urlpath=lab"
    binder_r_link = f"{binder_base_url}?urlpath=rstudio"
    binder_py_link = f"{binder_base_url}?filepath={REPO_PYTHON_OUTPUT}"

    md_doc = []
    md_doc.append(header)
    md_doc.append(
        f"### Renku: [![launch - renku](https://renkulab.io/renku-badge.svg)]({renku_base_url})\n"
    )
    md_doc.append(
        f"### Jupyter Lab: [![Binder](https://mybinder.org/badge_logo.svg)]({binder_lab_link})\n"
    )
    md_doc.append(
        f"### RStudio Server: [![Binder](https://mybinder.org/badge_logo.svg)]({binder_r_link})\n"
    )
    md_doc.append("## Overview of datasets\n")
    md_doc.append(
        f"| ID | Title (abbreviated to {TITLE_MAX_CHARS} chars) | Python marimo | Python Binder | Python Colab | R Colab | Python GitHub | R GitHub |\n"
    )
    md_doc.append("| :-- | :-- | :-- | :-- | :-- | :-- | :-- | :-- |\n")

    for idx in tqdm(data.index):
        identifier = data.loc[idx, "dataset_identifier"]
        # remove square brackets from title, since these break markdown links
        title_clean = data.loc[idx, "title"].replace("[", " ").replace("]", " ")
        if len(title_clean) > TITLE_MAX_CHARS:
            title_clean = title_clean[:TITLE_MAX_CHARS] + "…"

        ds_link = f"{BASELINK_DATASHOP}{identifier}"

        r_gh_link = f"[R GitHub]({baselink_r_gh}{identifier}.Rmd)"
        py_gh_link = f"[Python GitHub]({baselink_py_gh}{identifier}.ipynb)"
        py_colab_link = f"[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)]({baselink_py_colab}{identifier}.ipynb)"
        r_colab_link = f"[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)]({baselink_r_colab}{identifier}.ipynb)"
        py_binder_link = f"[![Jupyter Binder](https://mybinder.org/badge_logo.svg)]({binder_py_link}{identifier}.ipynb)"
        py_marimo_link = f"[![Open with  marimo](https://marimo.io/shield.svg)]({baselink_py_marimo}{identifier})"

        md_doc.append(
            f"| {identifier.split('@')[0]} | [{title_clean}]({ds_link}) | {py_marimo_link} | {py_binder_link} | {py_colab_link} | {r_colab_link} | {py_gh_link} | {r_gh_link} |\n"
        )

    md_doc = "".join(md_doc)

    with open(f"{TEMP_PREFIX}README.md", "w", encoding="utf-8") as file:
        file.write(md_doc)


# CREATE CODE FILES ---------------------------------------------------------- #

GET_DATASET_PY_SOURCE = load_shared_source(SHARED_GET_DATASET_PY)
GET_DATASET_R_SOURCE = load_shared_source(SHARED_GET_DATASET_R)
EDA_PY_SECTIONS = load_shared_sections(SHARED_ANALYZE_DATA_PY)
EDA_R_SECTIONS = load_shared_sections(SHARED_ANALYZE_DATA_R)

df = get_current_json()
df = sort_data(df)
prune_stale_files(df)
df = prepare_data_for_codebooks(df)
df = fetch_dataset_fields(df)

create_python_notebooks(df)
create_rmarkdown(df)
create_rnotebooks(df)
create_marimo_apps(df)

header = get_header(len(df))
create_overview(df, header)
