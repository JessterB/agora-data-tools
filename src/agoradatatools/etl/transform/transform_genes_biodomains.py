import pandas as pd

from agoradatatools.etl.transform.utils import *


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
    n_biodomain_terms = count_grouped_total(
        genes_biodomains, "biodomain", "go_terms", "n_biodomain_terms"
    )

    # Count the number of go_terms associated with each gene, ignoring biodomain
    n_gene_total_terms = count_grouped_total(
        genes_biodomains, "ensembl_gene_id", "go_terms", "n_gene_total_terms"
    )

    # Count the number of go_terms associated with each gene / biodomain combo
    n_gene_biodomain_terms = count_grouped_total(
        genes_biodomains,
        ["ensembl_gene_id", "biodomain"],
        "go_terms",
        "n_gene_biodomain_terms",
    )

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
        genes_biodomains["n_gene_biodomain_terms"]
        / genes_biodomains["n_gene_total_terms"]
        * 100
    ).round(decimals=2)

    # Remove n_gene_total_terms column
    genes_biodomains = genes_biodomains.drop(columns="n_gene_total_terms")

    genes_biodomains = nest_fields(
        df=genes_biodomains,
        grouping="ensembl_gene_id",
        new_column="gene_biodomains",
        drop_columns="ensembl_gene_id",
    )

    return genes_biodomains
