def transform_rnaseq_differential_expression(datasets: dict):
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
