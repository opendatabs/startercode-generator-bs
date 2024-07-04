# IMPORTS -------------------------------------------------------------------- #

import pandas as pd
import requests
import json
import re
from datetime import datetime
from tqdm import tqdm
import credentials

import warnings
warnings.simplefilter(action='ignore', category=FutureWarning)


# CONSTANTS ------------------------------------------------------------------ #

PATH_METADATA = "_metadata_json/"
BASELINK_DATASHOP = "https://data.bs.ch/explore/dataset/"

PROVIDER = "Statistisches Amt des Kantons Basel-Stadt - Fachstelle OGD"
SHOP_METADATA_LINK = "https://data.bs.ch/api/explore/v2.1/catalog/datasets/100057/exports/json"
CONTACT = "Fachstelle für OGD Basel-Stadt | opendata@bs.ch"

GITHUB_ACCOUNT = "opendatabs"
REPO_NAME = "startercode-opendatabs"
REPO_BRANCH = "main"
REPO_R_MARKDOWN_OUTPUT = "01_r-markdown/"
REPO_R_NOTEBOOK_OUTPUT = "02_r-notebook/"
REPO_PYTHON_OUTPUT = "03_python/"
TEMP_PREFIX = "_work/"
TEMP_PREFIX_RENKU = "_work_renku/"

TEMPLATE_FOLDER = "_templates/"
TEMPLATE_HEADER = "template_header.md"
TEMPLATE_PYTHON = "template_python.ipynb"
TEMPLATE_RMARKDOWN = "template_rmarkdown.Rmd"
TEMPLATE_RNOTEBOOK = "template_rnotebook.ipynb"

TODAY_DATE = datetime.today().strftime('%Y-%m-%d')
TODAY_DATETIME = datetime.today().strftime("%Y-%m-%d %H:%M:%S")

# max length of dataset title in markdown table
TITLE_MAX_CHARS = 200

# select metadata features that are going to be displayed in starter code files
KEYS_DATASET = ['dataset_identifier', 'title', 'description', 'contact_name',
                'issued', 'modified', 'rights',
                'temporal_coverage_start_date', 'temporal_coverage_end_date',
                'themes', 'keywords', 'publisher', 'reference']


# FUNCTIONS ------------------------------------------------------------------ #
def get_current_json():
    """Request metadata catalogue from data shop"""
    res = requests.get(SHOP_METADATA_LINK, proxies=credentials.proxies)
    # # save with date to allow for later error and change analysis
    # with open(f"{PATH_METADATA}{TODAY_DATE}.json", "wb") as file:
    # file.write(res.content)
    data = json.loads(res.text)
    return pd.DataFrame(data)


def sort_data(data):
    """Sort by integer prefix of identifier"""
    data["id_short"] = df.dataset_identifier.apply(
        lambda x: x.split("@")[0]).astype(int)
    data.sort_values("id_short", inplace=True)
    data.reset_index(drop=True, inplace=True)
    return data


def prepare_data_for_codebooks(data):
    """Prepare metadata from catalogue in order to create code files"""
    data["metadata"] = None

    # iterate over all datasets and compose refined data for markdown and code cells
    for idx in tqdm(data.index):
        md = [f"- **{k.capitalize()}** `{data.loc[idx, k]}`\n" for k in KEYS_DATASET]
        data.loc[idx, "metadata"] = "".join(md)

    return data


def create_python_notebooks(data):
    """Create Jupyter Notebooks with Python starter code"""
    for idx in tqdm(data.index):
        with open(f"{TEMPLATE_FOLDER}{TEMPLATE_PYTHON}") as file:
            py_nb = file.read()

        # populate template with metadata
        identifier = data.loc[idx, "dataset_identifier"]
        py_nb = py_nb.replace("{{ PROVIDER }}", PROVIDER)
        py_nb = py_nb.replace("{{ DATASET_TITLE }}", re.sub(
            "\"", "\'", data.loc[idx, "title"]))

        py_nb = py_nb.replace("{{ DATASET_DESCRIPTION }}", re.sub(
            "\"", "\'", data.loc[idx, "description"]))
        py_nb = py_nb.replace("{{ DATASET_IDENTIFIER }}", identifier)
        py_nb = py_nb.replace("{{ DATASET_METADATA }}", re.sub(
            "\"", "\'", data.loc[idx, "metadata"]))

        ds_link = f'[Direct data shop link for dataset]({BASELINK_DATASHOP}{identifier})'
        py_nb = py_nb.replace("{{ DATASHOP_LINK }}", ds_link)

        download_link = f"{BASELINK_DATASHOP}{identifier}/download"
        code_block = f"df = get_dataset('{download_link}')"
        py_nb = py_nb.replace("{{ LOAD_DATA }}", code_block)

        py_nb = py_nb.replace("{{ CONTACT }}", CONTACT)

        # to properly populate the code cell for data set import
        # we need to operate on the actual JSON rather than use simple string replacement
        py_nb = json.loads(py_nb, strict=False)

        # save to disk
        with open(f'{TEMP_PREFIX}{REPO_PYTHON_OUTPUT}{identifier}.ipynb', 'w') as file:
            file.write(json.dumps(py_nb))
        with open(f'{TEMP_PREFIX_RENKU}{REPO_PYTHON_OUTPUT}{identifier}.ipynb', 'w') as file:
            file.write(json.dumps(py_nb))


def create_rmarkdown(data):
    """Create R Markdown files with R starter code"""
    for idx in tqdm(data.index):
        with open(f"{TEMPLATE_FOLDER}{TEMPLATE_RMARKDOWN}") as file:
            rmd = file.read()

        # populate template with metadata
        identifier = data.loc[idx, "dataset_identifier"]
        rmd = rmd.replace("{{ DATASET_TITLE }}", data.loc[idx, "title"])
        rmd = rmd.replace("{{ PROVIDER }}", PROVIDER)
        rmd = rmd.replace("{{ TODAY_DATE }}", TODAY_DATE)
        rmd = rmd.replace("{{ DATASET_IDENTIFIER }}", identifier)
        rmd = rmd.replace("{{ DATASET_DESCRIPTION }}",
                          data.loc[idx, "description"])
        rmd = rmd.replace("{{ DATASET_METADATA }}", data.loc[idx, "metadata"])

        ds_link = f'[Direct data shop link for dataset]({BASELINK_DATASHOP}{identifier})'
        rmd = rmd.replace("{{ DATASHOP_LINK }}", ds_link)

        download_link = f"{BASELINK_DATASHOP}{identifier}/download?format=csv&timezone=Europe%2FZurich"
        code_block = f"df <- get_dataset('{download_link}')"
        rmd = rmd.replace("{{ LOAD_DATA }}", code_block)

        rmd = rmd.replace("{{ CONTACT }}", CONTACT)

        # save to disk
        with open(f'{TEMP_PREFIX}{REPO_R_MARKDOWN_OUTPUT}{identifier}.Rmd', 'w', encoding='utf-8') as file:
            file.write("".join(rmd))
        with open(f'{TEMP_PREFIX_RENKU}{REPO_R_MARKDOWN_OUTPUT}{identifier}.Rmd', 'w', encoding='utf-8') as file:
            file.write("".join(rmd))

def create_rnotebooks(data):
    """Create Jupyter Notebooks with R starter code"""
    for idx in tqdm(data.index):
        with open(f"{TEMPLATE_FOLDER}{TEMPLATE_RNOTEBOOK}") as file:
            r_nb = file.read()

        # populate template with metadata
        identifier = data.loc[idx, "dataset_identifier"]
        r_nb = r_nb.replace("{{ PROVIDER }}", PROVIDER)
        r_nb = r_nb.replace("{{ DATASET_TITLE }}", re.sub(
            "\"", "\'", data.loc[idx, "title"]))

        r_nb = r_nb.replace("{{ DATASET_DESCRIPTION }}", re.sub(
            "\"", "\'", data.loc[idx, "description"]))
        r_nb = r_nb.replace("{{ DATASET_IDENTIFIER }}", identifier)
        r_nb = r_nb.replace("{{ DATASET_METADATA }}", re.sub(
            "\"", "\'", data.loc[idx, "metadata"]))
        r_nb = r_nb.replace("{{ TODAY_DATE }}", TODAY_DATE)
        ds_link = f'[Direct data shop link for dataset]({BASELINK_DATASHOP}{identifier})'
        r_nb = r_nb.replace("{{ DATASHOP_LINK }}", ds_link)

        download_link = f"{BASELINK_DATASHOP}{identifier}/download"
        code_block = f"df = get_dataset('{download_link}')"
        r_nb = r_nb.replace("{{ LOAD_DATA }}", code_block)

        r_nb = r_nb.replace("{{ CONTACT }}", CONTACT)

        # to properly populate the code cell for data set import
        # we need to operate on the actual JSON rather than use simple string replacement
        r_nb = json.loads(r_nb, strict=False)

        # save to disk
        with open(f'{TEMP_PREFIX}{REPO_R_NOTEBOOK_OUTPUT}{identifier}.ipynb', 'w') as file:
            file.write(json.dumps(r_nb))
        with open(f'{TEMP_PREFIX_RENKU}{REPO_R_NOTEBOOK_OUTPUT}{identifier}.ipynb', 'w') as file:
            file.write(json.dumps(r_nb))

def get_header(dataset_count):
    """Retrieve header template and populate with date and count of data records"""
    with open(f"{TEMPLATE_FOLDER}{TEMPLATE_HEADER}", encoding='utf-8') as file:
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

    renku_base_url = f"https://renkulab.io/projects/{GITHUB_ACCOUNT}/{REPO_NAME}/sessions/new?autostart=1"
    binder_base_url = f"https://mybinder.org/v2/gh/{GITHUB_ACCOUNT}/{REPO_NAME}/{REPO_BRANCH}"
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
    md_doc.append(f"## Overview of datasets\n")
    md_doc.append(
        f"| ID | Title (abbreviated to {TITLE_MAX_CHARS} chars) | Python Binder (Jupyter Notebook) | Python Colab | R Colab | Python GitHub | R GitHub |\n")
    md_doc.append("| :-- | :-- | :-- | :-- | :-- | :-- | :-- |\n")

    for idx in tqdm(data.index):
        identifier = data.loc[idx, "dataset_identifier"]
        # remove square brackets from title, since these break markdown links
        title_clean = data.loc[idx, "title"].replace(
            "[", " ").replace("]", " ")
        if len(title_clean) > TITLE_MAX_CHARS:
            title_clean = title_clean[:TITLE_MAX_CHARS] + "…"

        ds_link = f'{BASELINK_DATASHOP}{identifier}'

        r_gh_link = f'[R GitHub]({baselink_r_gh}{identifier}.Rmd)'
        py_gh_link = f'[Python GitHub]({baselink_py_gh}{identifier}.ipynb)'
        py_colab_link = f'[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)]({baselink_py_colab}{identifier}.ipynb)'
        r_colab_link = f'[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)]({baselink_r_colab}{identifier}.ipynb)'
        py_binder_link = f'[![Jupyter Binder](https://mybinder.org/badge_logo.svg)]({binder_py_link}{identifier}.ipynb)'

        md_doc.append(
            f"| {identifier.split('@')[0]} | [{title_clean}]({ds_link}) |{py_binder_link} | {py_colab_link} | {r_colab_link} | {py_gh_link} | {r_gh_link} |\n")

    md_doc = "".join(md_doc)

    with open(f"{TEMP_PREFIX}README.md", "w", encoding='utf-8') as file:
        file.write(md_doc)
    with open(f"{TEMP_PREFIX_RENKU}README.md", "w", encoding='utf-8') as file:
        file.write(md_doc)


# CREATE CODE FILES ---------------------------------------------------------- #

df = get_current_json()
df = sort_data(df)
df = prepare_data_for_codebooks(df)

create_python_notebooks(df)
create_rmarkdown(df)
create_rnotebooks(df)

header = get_header(len(df))
create_overview(df, header)
