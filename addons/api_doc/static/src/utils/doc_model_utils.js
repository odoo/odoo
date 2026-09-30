const FIELDS_DEFAULT = [
    {
        types: ["integer", "float", "many2one_reference"],
        value: 0,
    },
    {
        types: ["char", "selection", "html"],
        value: "",
    },
    {
        types: ["boolean", "many2one"],
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
                vals_list: [getCreateDict(model)],
            },
        },
        read: {
            request: {
                ids: [0, 1],
                fields: ["display_name", "name", "create_date"],
            },
        },
        search: {
            responseCode: `\
[
    1,
    2
]`,
            request: {
                domain: [["display_name", "ilike", "a%"]],
            },
        },
        search_count: {
            responseCode: `10`,
            request: {
                domain: [["display_name", "ilike", "a%"]],
            },
        },
        search_read: {
            responseCode: `10`,
            request: {
                domain: [["display_name", "ilike", "a%"]],
                fields: ["display_name"],
                limit: 20,
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
                vals: {
                    display_name: "Dope New Name",
                },
            },
        },
        name_search: {
            request: {
                domain: [["display_name", "ilike", "a%"]],
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
                fields: ["id", "display_name", "write_date"],
                groupby: "write_date",
                domain: [["display_name", "ilike", "a%"]],
            },
        },
    };
}

export function getParameterDefaultValue(name, parameter) {
    if ("default" in parameter) {
        return parameter.default;
    } else if (/\bdomaintype\b/i.test(parameter.type)) {
        return [[ "display_name", "ilike", "a%"]];
    } else if (/\bstr\b/i.test(parameter.type)) {
        return "";
    } else if (/\b(int|float|complex)\b/i.test(parameter.type)) {
        return 0;
    } else if (/\bbool\b/i.test(parameter.type)) {
        return false;
    } else if (
        /args/i.test(name) ||
        /\b(list|sequence|collection|tuple|range|set)\b/i.test(parameter.annotation)
    ) {
        return [];
    } else if (/dict/i.test(parameter.annotation)) {
        return {};
    } else {
        return "";
    }
}
