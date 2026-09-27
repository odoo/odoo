export function mockDocIndex(modelNames = ["M1", "M2"]) {
    return {
        models: modelNames.map((name) => ({
            model: name,
            name: `Model_${name}`,
            fields: {
                [`field_1_${name}`]: { string: `Field 1 ${name}` },
                [`field_2_${name}`]: { string: `Field 2 ${name}` },
            },
            methods: [
                `method_1_${name}`,
                `method_2_${name}`,
            ],
        }))
    };
}

export function mockDocModel(modelName) {
    const field_1_name = `field_1_${modelName}`;
    const field_2_name = `field_2_${modelName}`;
    const field_1_string = `Field 1 ${modelName}`;
    const field_2_string = `Field 2 ${modelName}`;

    const method_1_name = `method_1_${modelName}`;
    const method_2_name = `method_2_${modelName}`;

    return {
        doc: null,
        model: modelName,
        name: `Model_${modelName}`,
        fields: {
            [field_1_name]: mockField(field_1_name, field_1_string, "string"),
            [field_2_name]: mockField(field_2_name, field_2_string, "boolean"),
        },
        methods: {
            [method_1_name]: mockMethod(modelName, "None"),
            [method_2_name]: mockMethod(modelName, "list[int]"),
        },
    };
}

function mockField(name, string, type, module="test_module") {
	return {
        name,
        string,
        type,
        module,
        change_default: false,
        company_dependent: false,
        default_export_compatible: false,
        depends: [],
        exportable: true,
        groupable: true,
        manual: false,
        readonly: false,
        required: false,
        searchable: true,
        sortable: true,
        store: true,
	};
}

function mockMethod(model, returnType, module="test_module") {
    return {
        api: ["model"],
        doc: `<div class="document">\n<p>This is a method.</p>\n</div>`,
        model,
        module,
        parameters: {
            param_a: mockParameter("param_a", "list[int]"),
            param_b: mockParameter("param_b", "int"),
        },
        raise: {
            TestError: "<ul class=\"simple\">\n<li>if something</li>\n<li>if something else</li>\n</ul>"
        },
        return: {
            annotation: returnType,
            doc: "<p>Some return doc</p>"
        },
        signature: `(param_a=None, param_b=None) -> ${returnType}`,
    };
}

function mockParameter(name, type) {
    return {
        annotation: type,
        default: null,
        doc: `<p>this is ${name}</p>`,
    };
}

