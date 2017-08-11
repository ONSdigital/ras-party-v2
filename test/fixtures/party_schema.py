schema = {
    "type": "object",
    "properties": {
        "sampleUnitRef": {"type": "string"},
        "sampleUnitType": {"enum": ["B", "BI"]},
        "attributes": {
            "type": "object",
            "properties": {
                "ruref": {"type": "string"},
                "birthdate": {"type": "string"},
                "cellNo": {"type": "string"},
                "checkletter": {"type": "string"},
                "currency": {"type": "string"},
                "entname1": {"type": "string"},
                "entname2": {"type": "string"},
                "entname3": {"type": "string"},
                "entref": {"type": "string"},
                "entremkr": {"type": "string"},
                "formType": {"type": "string"},
                "formtype": {"type": "string"},
                "froempment": {"type": "integer"},
                "frosic2007": {"type": "string"},
                "frosic92": {"type": "string"},
                "frotover": {"type": "integer"},
                "inclexcl": {"type": "string"},
                "legalstatus": {"type": "string"},
                "region": {"type": "string"},
                "runame1": {"type": "string"},
                "runame2": {"type": "string"},
                "rusic2007": {"type": "string"},
                "rusic92": {"type": "string"},
                "seltype": {"type": "string"},
                "tradstyle1": {"type": "string"},
                "cell_no": {"type": "integer"}
            },
            "required": ["runame1", "runame2"]
        }
    },
    "required": ["sampleUnitRef", "sampleUnitType"]
}
