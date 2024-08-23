"""Function for transforming proteomics data. This function is currently only used for LFQ
proteomics.
"""

import pandas as pd


def transform_proteomics(df: pd.DataFrame) -> pd.DataFrame:
    """Filters out rows that have "CON__" in their uniqid. This label indicates that the protein
    is a known contaminant and should be removed from the final data set. Rows with an NA uniqid
    are also removed.

    Args:
        df (pd.DataFrame]): pandas DataFrame containing proteomics data. Must contain a column
                            called "uniqid".

    Returns:
        pd.DataFrame: a DataFrame that is identical to the input DataFrame but with rows containing
                      "CON__" in the uniqid removed.
    """
    # Checking for "== False" has the benefit of removing rows with NA uniqid values as well,
    # as contains() returns NA for those values.
    df = df[df["uniqid"].str.contains("CON__") == False]
    return df
