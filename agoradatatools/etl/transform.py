import pandas as pd

def standardize_column_names(df: pd.core.frame.DataFrame) -> pd.DataFrame:
    """Takes in a dataframe and performs standard operations on column names
    :param df: a dataframe
    :return: a dataframe
    """

    df.columns = df.columns.str.replace("[#,@,&,*,^,?,(,),%,$,#,!,/]", "")
    df.columns = df.columns.str.replace("[' ', '-', '.']", "_")
    df.columns = map(str.lower, df.columns)

    return df


def standardize_values(df: pd.core.frame.DataFrame) -> pd.DataFrame:
    """
    Finds non-compliant values and corrects them
    *if more data cleaning options need to be added to this,
    this needs to be refactored to another function
    :param df: a dataframe
    :return: a dataframe
    """

    for column in df:
        dt = df[column].dtype
        if dt == int or dt == float:
            df[column] = df[column].fillna(0)
        else:
            df[column] = df[column].fillna("")

    df = df.replace(["NA", "n/a", "N/A", "na", "n/A", "N/a", "Na", "nA"], "")

    return df

def rename_columns(df: pd.core.frame.DataFrame, column_map: dict) -> pd.DataFrame:
    """Takes in a dataframe and renames columns according to the mapping provided
    :param df: a dataframe
    :param column_map: a dict with the mappoing for the columns to be renamed
    :return: a dataframe
    """
    try:
        df = df.rename(columns=column_map)
    except TypeError:
        print("Column mapping must be a dictionary")
        return df

    return df


def subset_columns(df: pd.core.frame.DataFrame, start: int, end: int) -> pd.core.frame.DataFrame:
    return df[df.columns[start:end]]

def join_datasets(left: pd.core.frame.DataFrame, right: pd.core.frame.DataFrame, how: str, on: str):
    return pd.merge(left=left, right=right, how=how, on=on)

def transform_team_info(datasets: dict):
    left = datasets['syn12615624'] # team_info
    right = datasets['syn12615633'] # team_member_info

    right = right.groupby('team')\
        .apply(lambda x: x[x.columns.difference(['team'])] .fillna('').to_dict(orient='records'))\
        .reset_index(name="members")

    return join_datasets(left=left, right=right, how='left', on='team')


def apply_custom_transformations(datasets: dict, dataset_name: str):

    if type(datasets) is not dict or type(dataset_name) is not str:
        return None

    print(list(datasets))

    if dataset_name == "overall_scores":
        df = datasets['syn25575156']
        return subset_columns(df=df, start=0, end=6)
    elif dataset_name == "team_info":
        return transform_team_info(datasets=datasets)

    else:
        return None