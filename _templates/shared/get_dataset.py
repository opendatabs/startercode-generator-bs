# Canonical data-loading code, shared by template_python.ipynb and template_marimo.py
# via updater.py. Not a standalone module: os/io/pd/requests/tqdm are expected to
# already be imported in the scope this gets spliced into.


def ensure_data_dir() -> str:
    data_path = os.path.join(os.getcwd(), "..", "data")
    os.makedirs(data_path, exist_ok=True)
    return data_path


def download_csv_chunk(
    session: requests.Session,
    dataset_id: str,
    extra_params: dict | None = None,
) -> pd.DataFrame:
    base_url = "https://data.bs.ch/api/explore/v2.1"
    url = f"{base_url}/catalog/datasets/{dataset_id}/exports/csv"

    params = {
        "timezone": "Europe/Zurich",
        "use_labels": "false",
    }
    if extra_params:
        params.update(extra_params)

    r = session.get(url, params=params)
    r.raise_for_status()

    buf = io.BytesIO(r.content)

    df = pd.read_csv(
        buf,
        sep=";",
        on_bad_lines="warn",
        encoding_errors="ignore",
        low_memory=False,
    )

    return df


def pick_best_facet(facets_json: dict, max_rows_per_chunk: int) -> tuple[str | None, list[str]]:
    """
    Choose a facet column where each bucket has <= max_rows_per_chunk rows.
    Among all such columns, pick the one with the smallest worst-case bucket.
    Returns (facet_name, list_of_values) or (None, []) if nothing suitable.
    """
    best_name = None
    best_values: list[str] = []
    best_max_bucket = None

    for facet in facets_json.get("facets", []):
        facet_name = facet.get("name")
        value_list = facet.get("facets", [])
        if not facet_name or not value_list:
            continue

        counts = [v.get("count", 0) for v in value_list]
        if not counts:
            continue

        max_bucket = max(counts)
        if max_bucket > max_rows_per_chunk:
            # this facet would still exceed the chunk limit for some values
            continue

        if best_max_bucket is None or max_bucket < best_max_bucket:
            best_max_bucket = max_bucket
            best_name = facet_name
            best_values = [v.get("value") for v in value_list if v.get("value") is not None]

    return best_name, best_values


def get_dataset(dataset_id: str, max_rows_per_chunk: int = 50_000) -> pd.DataFrame:
    """
    Download a dataset from data.bs.ch.

    - For small datasets (<= max_rows_per_chunk): single CSV export.
    - For large datasets:
        * Inspect /facets to find a good splitting column.
        * Download one CSV per facet value via refine.<col>=<value>.
        * Additionally download rows where that column is NULL via q=#null(<col>).

    The combined result is written to ../data/{dataset_id}.csv and returned as a DataFrame.
    """
    base_url = "https://data.bs.ch/api/explore/v2.1"
    records_url = f"{base_url}/catalog/datasets/{dataset_id}/records"
    facets_url = f"{base_url}/catalog/datasets/{dataset_id}/facets"

    session = requests.Session()
    common_params = {
        "timezone": "Europe/Zurich",
        "use_labels": "false",
    }

    # 1) Get total_count via /records
    r = session.get(records_url, params={**common_params, "limit": 1})
    r.raise_for_status()
    meta = r.json()
    total_count = meta.get("total_count", 0)

    if not isinstance(total_count, int):
        # fall back to simple export if we can't read total_count
        total_count = 0

    # 2) Small dataset: single CSV export
    if total_count == 0 or total_count <= max_rows_per_chunk:
        df = download_csv_chunk(session, dataset_id, extra_params={})
        data_path = ensure_data_dir()
        csv_path = os.path.join(data_path, f"{dataset_id}.csv")
        df.to_csv(csv_path, index=False)
        return df

    # 3) Large dataset: inspect /facets to decide how to split
    r = session.get(facets_url, params=common_params)
    r.raise_for_status()
    facets_json = r.json()

    facet_name, facet_values = pick_best_facet(facets_json, max_rows_per_chunk=max_rows_per_chunk)

    if facet_name is None or not facet_values:
        raise RuntimeError(
            f"Could not find a facet column to split dataset {dataset_id} into "
            f"chunks of <= {max_rows_per_chunk} rows. Please handle this dataset manually."
        )

    dfs: list[pd.DataFrame] = []

    # 4) Download each facet value (refine.<facet_name>=value), plus NULLs
    null_query = {"qv1": f"#null({facet_name})"}
    try:
        df_null = download_csv_chunk(session, dataset_id, extra_params=null_query)
        if not df_null.empty:
            dfs.append(df_null)
    except requests.HTTPError as e:
        print(f"Warning: NULL download for {facet_name} failed: {e}")

    for v in tqdm(facet_values, desc=f"Downloading {dataset_id} (split by {facet_name})"):
        params = {"refine": f'{facet_name}:"{v}"'}
        df_chunk = download_csv_chunk(session, dataset_id, extra_params=params)
        dfs.append(df_chunk)

    # 5) Combine all parts, save to a single CSV, return DataFrame
    if dfs:
        full_df = pd.concat(dfs, ignore_index=True)
    else:
        full_df = pd.DataFrame()

    data_path = ensure_data_dir()
    csv_path = os.path.join(data_path, f"{dataset_id}.csv")
    full_df.to_csv(csv_path, index=False)

    return full_df
