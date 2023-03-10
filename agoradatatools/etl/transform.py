import numpy as np
import pandas as pd


def standardize_column_names(df: pd.DataFrame) -> pd.DataFrame:
    """Takes in a dataframe replaces problematic characters in column names
    and makes column names all lowercase characters

    Args:
        df (pd.DataFrame): DataFrame with columns to be standardized

    Returns:
        pd.DataFrame: New dataframe with cleaned column names
    """

    df.columns = df.columns.str.replace(
        "[#@&*^?()%$#!/]", "", regex=True
    )  # the commas were unnessesary and were breaking the prelacement of '-' characters
    df.columns = df.columns.str.replace("[ -.]", "_", regex=True)
    df.columns = map(str.lower, df.columns)

    return df


def standardize_values(df: pd.DataFrame) -> pd.DataFrame:
    """Finds non-compliant values and corrects them
    *if more data cleaning options need to be added to this,
    this needs to be refactored to another function

    Args:
        df (pd.DataFrame): DataFrame with values to be standardized

    Returns:
        pd.DataFrame: Resulting DataFrame with standardized values
    """
    try:
        df.replace(["n/a", "N/A", "n/A", "N/a"], np.nan, regex=True, inplace=True)
    except TypeError:  # I could not get this to trigger without mocking replace
        print("Error comparing types.")

    return df


def rename_columns(df: pd.DataFrame, column_map: dict) -> pd.DataFrame:
    """Takes in a dataframe and renames columns according to the mapping provided

    Args:
        df (pd.DataFrame): DataFrame with columns to be renamed
        column_map (dict): Dictionary mapping original column names to new columns

    Returns:
        pd.DataFrame: DataFrame with new columns names
    """
    try:
        df.rename(columns=column_map, inplace=True)
    except TypeError:
        print("Column mapping must be a dictionary")
        return df

    return df

    """
    This will create a dictionary object with the result of the grouping provided
    :param df: a dataframe
    :param grouping: a string containing the column to group by
    :param new_column: a string with the name of the new column that will contain
    the nested field
    :param drop_columns: a list of column names to drop (remove) from the
    nested dictionary. Optional argument, defaults to empty list.
    :return: a dataframe
    """


def nest_fields(
    df: pd.DataFrame, grouping: str, new_column: str, drop_columns: list = []
) -> pd.DataFrame:
    """Collapses the provided DataFrame into 2 columns:
    1. The grouping column
    2. A column containing a nested dictionary with the data from the rest of the DataFrame

    Args:
        df (pd.DataFrame): DataFrame to be collapsed
        grouping (str): The column that you want to group by
        new_column (str): the new column created to contain the nested dictionaries created
        drop_columns (list, optional): List of columns to leave out of the new nested dictionary. Defaults to [].

    Returns:
        pd.DataFrame: New 2 column DataFrame with group and nested dictionaries
    """
    return (
        df.groupby(grouping)
        .apply(
            lambda row: row.replace({np.nan: None})
            .drop(columns=drop_columns)
            .to_dict("records")
        )
        .reset_index()
        .rename(columns={0: new_column})
    )


def calculate_distribution(df: pd.DataFrame, col: str, is_scored, upper_bound) -> dict:
    if is_scored:
        df = df[df[is_scored] == "Y"]  # df does not have the isscored
    else:
        df = df[df.isin(["Y"]).any(axis=1)]

    if df[col].dtype == object:
        df[col] = df[col].astype(float)

    obj = {}

    """
    In order to smooth out the bins and make sure the entire range from 0
    to the theoretical maximum value has been found, we create a copy of the
    column with both 0 and that maximum value added to it.  We use the copy to calculate 
    distributions and bins, and subtract the values at the end
    """
    distribution = df[col].append(pd.Series([0, upper_bound]), ignore_index=True)

    obj["distribution"] = list(
        pd.cut(
            distribution, bins=10, precision=3, include_lowest=True, right=True
        ).value_counts(sort=False)
    )
    obj["distribution"][
        0
    ] -= 1  # since this was calculated with the artificial 0 value, we subtract it
    obj["distribution"][
        -1
    ] -= 1  # since this was calculated with the artificial upper_bound, we subtract it

    discard, obj["bins"] = list(
        pd.cut(distribution, bins=10, precision=3, retbins=True)
    )
    obj["bins"] = np.around(obj["bins"].tolist()[1:], 2)
    base = [0, *obj["bins"][:-1]]
    obj["bins"] = zip(base, obj["bins"])
    obj["bins"] = list(obj["bins"])

    obj["min"] = np.around(df[col].min(), 4)
    obj["max"] = np.around(df[col].max(), 4)
    obj["mean"] = np.around(df[col].mean(), 4)
    obj["first_quartile"] = np.around(
        df[col].quantile(q=0.25, interpolation="midpoint")
    )
    obj["third_quartile"] = np.around(
        df[col].quantile(q=0.75, interpolation="midpoint")
    )

    return obj


def count_grouped_total(df: pd.DataFrame,
                        grouping: [str, list],
                        input_colname: str,
                        output_colname: str) -> pd.DataFrame:
    """For each unique item/combination in the column(s) specified by grouping,
    counts the number of unique items in the column [input_colname] that
    correspond to that grouping. The calculated counts are put in a new
    column and named with [output_colname].
    Args:
        df (pd.DataFrame): contains columns listed in grouping and
                           input_colname. May contain other columns as well, but
                           these will be dropped from the returned data frame.
        grouping (str or list): a string with a single column name, or a list of
                                strings for multiple column names
        input_colname (str): the name of the column to count
        output_colname (str): the name of the new column with calculated counts
    Returns:
        pd.DataFrame: a data frame containing the grouping column(s) and a
                      new column for output_colname, which contains the count of
                      unique items in input_colname for each grouping item.
    """
    df = (
        df.groupby(grouping)[input_colname]
        .nunique().reset_index()
        .rename(columns={input_colname: output_colname})
    )
    return df


def transform_genes_biodomains(datasets: dict) -> pd.DataFrame:
    """Takes dictionary of dataset DataFrames, extracts the genes_biodomains
    DataFrame, calculates some metrics on GO terms per gene / biodomain, and
    performs nest_fields on the final DataFrame. This results in a 2 column
    DataFrame grouped by "ensembl_gene_id" and includes a collapsed nested
    dictionary field "gene_biodomains"

    Args:
        datasets (dict[str, pd.DataFrame]): dictionary of dataset names mapped to their DataFrame

    Returns:
        pd.DataFrame: 2 column DataFrame grouped by "ensembl_gene_id" including
                      a collapsed nested dictionary field "gene_biodomains"
    """
    genes_biodomains = datasets["genes_biodomains"]
    interesting_columns = ["ensembl_gene_id", "biodomain", "go_terms"]
    genes_biodomains = genes_biodomains[interesting_columns].dropna()

    # Count the number of go_terms associated with each biodomain
    n_biodomain_terms = count_grouped_total(genes_biodomains,
                                            "biodomain",
                                            "go_terms",
                                            "n_biodomain_terms")

    # Count the number of go_terms associated with each gene, ignoring biodomain
    n_gene_total_terms = count_grouped_total(genes_biodomains,
                                             "ensembl_gene_id",
                                             "go_terms",
                                             "n_gene_total_terms")

    # Count the number of go_terms associated with each gene / biodomain combo
    n_gene_biodomain_terms = count_grouped_total(genes_biodomains,
                                                 ["ensembl_gene_id", "biodomain"],
                                                 "go_terms",
                                                 "n_gene_biodomain_terms")

    # Group rows by ensg and biodomain to produce nested lists of go_terms per ensg/biodomain
    genes_biodomains = (
        genes_biodomains.groupby(["ensembl_gene_id", "biodomain"])["go_terms"]
        .apply(list)
        .reset_index()
    )

    # Merge all the different count metrics into the main data frame so each
    # ensembl_gene_id / biodomain combo has an entry for each count
    genes_biodomains = (
        genes_biodomains.merge(n_gene_total_terms, on="ensembl_gene_id", how="left")
        .merge(n_biodomain_terms, on="biodomain", how="left")
        .merge(n_gene_biodomain_terms, on=["ensembl_gene_id", "biodomain"], how="left")
    )

    # Calculate percent linking terms:
    # n_gene_biodomain_terms / n_gene_total_terms * 100
    genes_biodomains["pct_linking_terms"] = (
        (genes_biodomains["n_gene_biodomain_terms"] /
         genes_biodomains["n_gene_total_terms"] * 100)
        .round(decimals=2)
    )

    # Remove n_gene_total_terms column
    genes_biodomains = genes_biodomains.drop(columns="n_gene_total_terms")

    genes_biodomains = nest_fields(
        df=genes_biodomains,
        grouping="ensembl_gene_id",
        new_column="gene_biodomains",
        drop_columns="ensembl_gene_id",
    )

    return genes_biodomains


def transform_overall_scores(df: pd.DataFrame) -> pd.DataFrame:
    interesting_columns = [
        "ensg",
        "hgnc_gene_id",
        "overall",
        "geneticsscore",
        "omicsscore",
        "literaturescore",
    ]

    # create mapping to deal with missing values as they take different shape across the fields
    scored = ["isscored_genetics", "isscored_omics", "isscored_lit"]
    mapping = dict(zip(interesting_columns[3:], scored))

    for field, is_scored in mapping.items():
        df.loc[lambda row: row[is_scored] == "N", field] = np.nan

    # LiteratureScore is a string in the source file, so convert to numeric
    df["literaturescore"] = pd.to_numeric(df["literaturescore"])

    # Remove identical rows (see AG-826)
    return df[interesting_columns].drop_duplicates()


def join_datasets(left: pd.DataFrame, right: pd.DataFrame, how: str, on: str):
    return pd.merge(left=left, right=right, how=how, on=on)


def transform_team_info(datasets: dict):
    team_info = datasets["team_info"]
    team_member_info = datasets["team_member_info"]

    team_member_info = (
        team_member_info.groupby("team")
        .apply(
            lambda x: x[x.columns.difference(["team"])]
            .fillna("")
            .to_dict(orient="records")
        )
        .reset_index(name="members")
    )

    return join_datasets(left=team_info, right=team_member_info, how="left", on="team")


def transform_rna_seq_data(datasets: dict):
    diff_exp_data = datasets["diff_exp_data"]

    diff_exp_data["study"].replace(
        to_replace={"MAYO": "MayoRNAseq", "MSSM": "MSBB"}, regex=True, inplace=True
    )
    diff_exp_data["sex"].replace(
        to_replace={
            "ALL": "males and females",
            "FEMALE": "females only",
            "MALE": "males only",
        },
        regex=True,
        inplace=True,
    )
    diff_exp_data["model"].replace(
        to_replace="\\.", value=" x ", regex=True, inplace=True
    )
    diff_exp_data["model"].replace(
        to_replace={"Diagnosis": "AD Diagnosis"}, regex=True, inplace=True
    )
    diff_exp_data["fc"] = 2 ** diff_exp_data["logfc"]
    diff_exp_data["model"] = diff_exp_data["model"] + " (" + diff_exp_data["sex"] + ")"

    diff_exp_data = diff_exp_data[
        [
            "ensembl_gene_id",
            "hgnc_symbol",
            "logfc",
            "fc",
            "ci_l",
            "ci_r",
            "adj_p_val",
            "tissue",
            "study",
            "model",
        ]
    ]

    return diff_exp_data


def transform_gene_info(
    datasets: dict, adjusted_p_value_threshold, protein_level_threshold
):
    """
    This function will perform transformations and incrementally create a dataset called gene_info.
    Each dataset will be left_joined onto gene_info, starting with gene_metadata.
    """
    gene_metadata = datasets["gene_metadata"]
    igap = datasets["igap"]
    eqtl = datasets["eqtl"]
    proteomics = datasets["proteomics"]
    rna_change = datasets["rna_expression_change"]
    proteomics_tmt = datasets["agora_proteomics_tmt"]
    target_list = datasets["target_list"]
    median_expression = datasets["median_expression"]
    druggability = datasets["druggability"]

    # Modify the data before merging

    # All genes in this list should have 'is_igap' = True when added to gene_info.
    # Creating the column here automatically adds the column in to gene_info
    # during merge, with True values correctly populated.
    igap["is_igap"] = True

    # Get the smallest adj_p_val for each gene, to determine significance
    rna_change = (
        rna_change.groupby("ensembl_gene_id")["adj_p_val"].agg("min").reset_index()
    )

    # Get the smallest cor_pval for each protein, to determine significance
    proteomics_concat = pd.concat([proteomics, proteomics_tmt])
    proteomics_concat = proteomics_concat.dropna(
        subset=["log2_fc", "cor_pval", "ci_lwr", "ci_upr"]
    )
    proteomics_concat = (
        proteomics_concat.groupby("ensembl_gene_id")["cor_pval"]
        .agg("min")
        .reset_index()
    )

    # these are the interesting columns of the druggability dataset
    useful_columns = [
        "geneid",
        "sm_druggability_bucket",
        "safety_bucket",
        "abability_bucket",
        "pharos_class",
        "classification",
        "safety_bucket_definition",
        "abability_bucket_definition",
    ]
    druggability = druggability[useful_columns]

    target_list = nest_fields(
        df=target_list, grouping="ensembl_gene_id", new_column="nominated_target"
    )

    median_expression = nest_fields(
        df=median_expression, grouping="ensembl_gene_id", new_column="median_expression"
    )

    druggability = nest_fields(
        df=druggability, grouping="geneid", new_column="druggability"
    )
    druggability.rename(columns={"geneid": "ensembl_gene_id"}, inplace=True)

    # Merge all the datasets

    gene_info = gene_metadata

    for dataset in [
        igap,
        eqtl,
        rna_change,
        proteomics_concat,
        target_list,
        median_expression,
        druggability,
    ]:
        gene_info = pd.merge(
            left=gene_info,
            right=dataset,
            on="ensembl_gene_id",
            how="outer",
            validate="one_to_one",
        )

    # Populate values for rows that didn't exist in the individual datasets

    gene_info.fillna(
        {"is_igap": False, "has_eqtl": False, "adj_p_val": -1, "cor_pval": -1},
        inplace=True,
    )

    # fillna doesn't work for creating an empty array, need this function instead
    gene_info["alias"] = gene_info.apply(
        lambda row: row["alias"]
        if isinstance(row["alias"], np.ndarray)
        else np.ndarray(0, dtype=object),
        axis=1,
    )

    gene_info["rna_brain_change_studied"] = gene_info["adj_p_val"] != -1
    gene_info["rna_in_ad_brain_change"] = (
        (gene_info["adj_p_val"] <= adjusted_p_value_threshold) &
        gene_info["rna_brain_change_studied"]
    )

    gene_info["protein_brain_change_studied"] = gene_info["cor_pval"] != -1
    gene_info["protein_in_ad_brain_change"] = (
        (gene_info["cor_pval"] <= protein_level_threshold) &
        gene_info["protein_brain_change_studied"]
    )

    # create 'nominations' field
    gene_info["nominations"] = gene_info.apply(
        lambda row: len(row["nominated_target"])
        if isinstance(row["nominated_target"], list)
        else np.NaN,
        axis=1,
    )

    # Remove some extra columns that got added during merges
    gene_info = gene_info[
        [
            "ensembl_gene_id",
            "name",
            "summary",
            "symbol",
            "alias",
            "is_igap",
            "has_eqtl",
            "rna_in_ad_brain_change",
            "rna_brain_change_studied",
            "protein_in_ad_brain_change",
            "protein_brain_change_studied",
            "nominated_target",
            "median_expression",
            "druggability",
            "nominations",
        ]
    ]

    # Make sure there are no N/A Ensembl IDs
    gene_info = gene_info.dropna(subset=["ensembl_gene_id"])

    return gene_info


def transform_distribution_data(
    datasets: dict,
    overall_max_score,
    genetics_max_score,
    omics_max_score,
    lit_max_score,
):

    overall_scores = datasets["overall_scores"]
    interesting_columns = [
        "ensg",
        "overall",
        "geneticsscore",
        "omicsscore",
        "literaturescore",
    ]

    # create mapping to deal with missing values as they take different shape across the fields
    scored = ["isscored_genetics", "isscored_omics", "isscored_lit"]
    mapping = dict(zip(interesting_columns[2:], scored))
    mapping["overall"] = None

    # create mapping for max score values from config
    max_score = dict(
        zip(
            interesting_columns[1:],
            [overall_max_score, genetics_max_score, omics_max_score, lit_max_score],
        )
    )

    overall_scores = overall_scores[interesting_columns + scored]

    neo_matrix = {}
    for col in interesting_columns[1:]:  # excludes the ENSG
        neo_matrix[col] = calculate_distribution(
            overall_scores, col, mapping[col], max_score[col]
        )

    neo_matrix["target_risk_score"] = neo_matrix.pop("overall")
    neo_matrix["genetics_score"] = neo_matrix.pop("geneticsscore")
    neo_matrix["multi_omics_score"] = neo_matrix.pop("omicsscore")
    neo_matrix["literature_score"] = neo_matrix.pop("literaturescore")

    additional_data = [
        {"name": "Target Risk Score", "syn_id": "syn25913473", "wiki_id": "613107"},
        {"name": "Genetic Risk Score", "syn_id": "syn25913473", "wiki_id": "613104"},
        {"name": "Multi-omic Risk Score", "syn_id": "syn25913473", "wiki_id": "613106"},
        {"name": "Literature Score", "syn_id": "syn25913473", "wiki_id": "613105"},
    ]
    for col, additional in zip(neo_matrix.keys(), additional_data):
        neo_matrix[col]["name"] = additional["name"]
        neo_matrix[col]["syn_id"] = additional["syn_id"]
        neo_matrix[col]["wiki_id"] = additional["wiki_id"]

    return neo_matrix


def transform_rna_distribution_data(datasets: dict):
    # "datasets" contains the unprocessed RNA-seq data, which needs to go
    # through the same processing as before in order to use it here. 
    rna_df = transform_rna_seq_data(datasets)
    rna_df = rna_df[["tissue", "model", "logfc"]]

    rna_df = (
        rna_df.groupby(["tissue", "model"])
        .agg("describe")["logfc"]
        .reset_index()[["model", "tissue", "min", "max", "25%", "50%", "75%"]]
    )
    rna_df.rename(
        columns={"25%": "first_quartile", "50%": "median", "75%": "third_quartile"},
        inplace=True,
    )

    rna_df["IQR"] = rna_df["third_quartile"] - rna_df["first_quartile"]
    rna_df["min"] = rna_df["first_quartile"] - (1.5 * rna_df["IQR"])
    rna_df["max"] = rna_df["third_quartile"] + (1.5 * rna_df["IQR"])

    for col in ["min", "max", "median", "first_quartile", "third_quartile"]:
        rna_df[col] = np.around(rna_df[col], 4)

    rna_df.drop("IQR", axis=1, inplace=True)

    return rna_df


def transform_proteomics_distribution_data(
    proteomics_df: pd.DataFrame, datatype: str
) -> pd.DataFrame:
    """Transform proteomics data
    Args:
        proteomics_df (pd.DataFrame): Dataframe
        datatype (str): Data Type
    Returns:
        pd.DataFrame: Transformed data
    """
    proteomics_df = (
        proteomics_df.groupby(["tissue"])
        .agg("describe")["log2_fc"]
        .reset_index()[["tissue", "min", "max", "25%", "50%", "75%"]]
    )

    proteomics_df.rename(
        columns={"25%": "first_quartile", "50%": "median", "75%": "third_quartile"},
        inplace=True,
    )

    proteomics_df["IQR"] = (
        proteomics_df["third_quartile"] - proteomics_df["first_quartile"]
    )
    proteomics_df["min"] = proteomics_df["first_quartile"] - (
        1.5 * proteomics_df["IQR"]
    )
    proteomics_df["max"] = proteomics_df["third_quartile"] + (
        1.5 * proteomics_df["IQR"]
    )

    for col in ["min", "max", "median", "first_quartile", "third_quartile"]:
        proteomics_df[col] = np.around(proteomics_df[col], 4)

    proteomics_df.drop("IQR", axis=1, inplace=True)
    proteomics_df["type"] = datatype

    return proteomics_df


def create_proteomics_distribution_data(datasets: dict) -> pd.DataFrame:

    transformed = []
    for name, dataset in datasets.items():
        if name == "proteomics":
            transformed.append(
                transform_proteomics_distribution_data(
                    proteomics_df=dataset, datatype="LFQ"
                )
            )
        elif name == "proteomics_tmt":
            transformed.append(
                transform_proteomics_distribution_data(
                    proteomics_df=dataset, datatype="TMT"
                )
            )

    return pd.concat(transformed)


def apply_custom_transformations(datasets: dict, dataset_name: str, dataset_obj: dict):

    if type(datasets) is not dict or type(dataset_name) is not str:
        return None

    elif dataset_name == "genes_biodomains":
        return transform_genes_biodomains(datasets=datasets)
    if dataset_name == "overall_scores":
        df = datasets["overall_scores"]
        return transform_overall_scores(df=df)
    elif dataset_name == "distribution_data":
        return transform_distribution_data(
            datasets=datasets,
            overall_max_score=dataset_obj["custom_transformations"][
                "overall_max_score"
            ],
            genetics_max_score=dataset_obj["custom_transformations"][
                "genetics_max_score"
            ],
            omics_max_score=dataset_obj["custom_transformations"]["omics_max_score"],
            lit_max_score=dataset_obj["custom_transformations"]["lit_max_score"],
        )
    elif dataset_name == "team_info":
        return transform_team_info(datasets=datasets)
    elif dataset_name == "rnaseq_differential_expression":
        return transform_rna_seq_data(datasets=datasets)
    elif dataset_name == "gene_info":
        return transform_gene_info(
            datasets=datasets,
            adjusted_p_value_threshold=dataset_obj["custom_transformations"][
                "adjusted_p_value_threshold"
            ],
            protein_level_threshold=dataset_obj["custom_transformations"][
                "protein_level_threshold"
            ],
        )
    elif dataset_name == "rna_distribution_data":
        return transform_rna_distribution_data(datasets=datasets)
    elif dataset_name == "proteomics_distribution_data":
        return create_proteomics_distribution_data(datasets=datasets)
    else:
        return None
