const FIELDS_DEFAULT = [
    {
        types: ["integer", "float", "many2one", "many2one_reference"],
        value: 0,
    },
    {
        types: ["char", "selection", "html"],
        value: "",
    },
    {
        types: ["boolean"],
        value: false,
    },
    {
        types: ["datetime", "date"],
        value: Date.now.toString(),
    },
    {
        types: ["binary"],
        value: null,
    },
    {
        types: ["one2many", "many2many"],
        value: "[]",
    },
];

function getFieldDefaultValue(field) {
    for (const fieldDefault of FIELDS_DEFAULT) {
        if (fieldDefault.types.includes(field.type)) {
            return fieldDefault.value;
        }
    }
    return null;
}

export function getCreateDict(model) {
    const value = {};
    for (const fieldName in model.fields) {
        if (model.fields[fieldName].required) {
            value[fieldName] = getFieldDefaultValue(model.fields[fieldName]);
        }
    }
    return value;
}

export function getCrudMethodsExamples(model) {
    return {
        create: {
            responseCode: `true`,
            request: {
                kwargs: {
                    vals_list: [getCreateDict(model)],
                },
            },
        },
        read: {
            request: {
                ids: [0, 1],
                kwargs: {
                    fields: ["display_name", "name", "create_date"],
                },
            },
        },
        search: {
            responseCode: `\
[
    1,
    2
]`,
            request: {
                kwargs: {
                    domain: [["display_name", "ilike", "a%"]],
                },
            },
        },
        search_count: {
            responseCode: `10`,
            request: {
                kwargs: {
                    domain: [["display_name", "ilike", "a%"]],
                },
            },
        },
        unlink: {
            responseCode: `true`,
            request: {
                ids: [],
            },
        },
        write: {
            responseCode: `true`,
            request: {
                ids: [0],
                kwargs: {
                    values: {
                        display_name: "Dope New Name",
                    },
                },
            },
        },
        name_search: {
            request: {
                kwargs: {
                    domain: [["display_name", "ilike", "a%"]],
                },
            },
            responseCode: `\
[
    [
        1,
        "Record 1 Name"
    ],
    [
        2,
        "Record 2 Name"
    ]
]`,
        },
        read_group: {
            name: "read_group",
            request: {
                kwargs: {
                    fields: ["id", "display_name", "write_date"],
                    groupby: "write_date",
                    domain: [["display_name", "ilike", "a%"]],
                },
            },
        },
    };
}
