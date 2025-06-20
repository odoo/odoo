import { Component, useState, useEffect } from "@odoo/owl";
import { DocTable, TABLE_TYPES } from "@doc/components/doc_table";
import { getCrudMethodsExamples } from "@doc/utils/doc_model_utils";
import { DocMethod } from "@doc/components/doc_method";
import { DocLoadingIndicator } from "@doc/components/doc_loading_indicator";

const TYPE_COLORS = {
    "text-green": ["integer", "char", "boolean", "selection", "float"],
    "text-blue": ["html", "datetime", "date", "binary"],
    "text-orange": ["many2one", "many2many", "one2many", "many2one_reference"],
};

function getTypeColor(type) {
    for (const key in TYPE_COLORS) {
        if (TYPE_COLORS[key].includes(type)) {
            return key;
        }
    }
}

export class DocModel extends Component {
    static template = "web.DocModel";
    static components = {
        DocTable,
        DocMethod,
        DocLoadingIndicator,
    };
    static props = {};

    setup() {
        this.state = useState({
            model: undefined,
            modelData: { items: [] },
            crudMethods: [],
            methods: [],
            modules: [],
            activeModules: {
                core: true,
                base: false,
            },
            showModulesFilter: true,
        });

        this.modelStore = useState(this.env.modelStore);
        this.update();

        useEffect(
            () => {
                this.update();
            },
            () => [
                this.modelStore.activeModel,
                this.modelStore.activeMethod,
                this.modelStore.activeField,
            ]
        );
    }

    get modelName() {
        return this.state.model?.name ?? "";
    }

    get fieldsData() {
        let fields = [];
        if (this.state.model && this.state.model.fields) {
            fields = Object.values(this.state.model.fields);
        }

        const getTypeData = (fieldData) => {
            const data = {
                type: TABLE_TYPES.Code,
                value: fieldData.type,
                class: getTypeColor(fieldData.type),
            };

            if (fieldData.type === "selection") {
                data.subData = {
                    headers: ["Value", "Label"],
                    items: fieldData.selection,
                };
            }

            if (fieldData.relation) {
                data.relation = fieldData.relation;
            }

            return data;
        };

        fields = fields
            .filter((fieldData) => this.isModuleActive(fieldData.module))
            .map((fieldData) => [
                { type: TABLE_TYPES.Code, value: fieldData.name },
                getTypeData(fieldData),
                fieldData.string,
                {
                    type: TABLE_TYPES.Code,
                    value: fieldData.required ? "required" : "optional",
                    class: fieldData.required ? "text-red" : "text-muted",
                },
                {
                    type: TABLE_TYPES.Tooltip,
                    value: fieldData.help,
                },
                {
                    type: TABLE_TYPES.Code,
                    value: fieldData.module || "",
                },
                {
                    type: "active",
                    value: this.modelStore.activeField === fieldData.name,
                },
            ]);

        fields.sort((a, b) => a[0].value.localeCompare(b[0].value));

        return {
            headers: ["Name", "Type", "Description", "Required", "Help", "Module"],
            items: fields,
        };
    }

    async update() {
        if (!this.state.model || this.state.model.model !== this.modelStore.activeModel.model) {
            this.updateModel(this.modelStore.activeModel);
        }

        this.updateActiveMethod(this.modelStore.activeMethod);
        this.updateActiveField(this.modelStore.activeField);
    }

    updateModel(model) {
        const modelId = model.model;

        this.state.model = {
            model: modelId,
            name: model.name,
            doc: "",
            fields: null,
        };
        this.state.modelData = this.getModelData(this.state.model);
        this.state.methods = [];
        this.state.modules = [];

        this.modelStore.loadModel(modelId).then((model) => {
            if (this.state.model.model !== model.model) {
                return;
            }

            let modules = new Set();
            Object.values(model.fields).forEach((f) => f.module && modules.add(f.module));
            Object.values(model.methods).forEach((m) => m.module && modules.add(m.module));

            modules = [...modules];
            modules.sort((a, b) => (a === "core" ? -1 : b === "core" ? 1 : a.localeCompare(b)));
            this.state.modules = modules;

            this.state.model = model;
            this.state.modelData = this.getModelData(model);
            this.state.methods = this.getMethods(model.model, model.methods);

            const crudExamples = getCrudMethodsExamples(model);
            for (const method of this.state.methods) {
                if (method.name in crudExamples) {
                    method.request = crudExamples[method.name].request;
                    method.responseCode = crudExamples[method.name].responseCode;
                }
            }

            this.updateActiveMethod(this.modelStore.activeMethod);
            this.updateActiveField(this.modelStore.activeField);
        });
    }

    async updateActiveField(fieldName) {
        const fieldData = Object.values(this.state.model.fields || []).find(
            (f) => f.name === fieldName
        );
        if (fieldData) {
            this.state.activeModules[fieldData.module] = true;
            await new Promise((resolve) => requestAnimationFrame(resolve));
            await new Promise((resolve) => setTimeout(resolve));
            document
                .querySelector(".o-doc-table tr.border-color-primary")
                ?.scrollIntoView({ behavior: "smooth" });
        }
    }

    async updateActiveMethod(methodName) {
        const method = this.state.methods?.find((m) => m.name === methodName);
        if (method) {
            this.state.activeModules[method.module] = true;
            await new Promise((resolve) => requestAnimationFrame(resolve));
            await new Promise((resolve) => setTimeout(resolve));
            document.getElementById(methodName)?.scrollIntoView({ behavior: "smooth" });
        }
    }

    getModelData(model) {
        const items = [["Model Name", { type: "code", value: model.model }]];

        if (model.doc) {
            items.push(["Description", model.doc || ""]);
        }

        return { items };
    }

    isModuleActive(module) {
        return !module || this.state.activeModules[module];
    }

    getMethods(modelId, methods) {
        const modules = {};

        for (const methodName in methods) {
            const method = methods[methodName];

            if (!(method.module in modules)) {
                modules[method.module] = [];
            }

            modules[method.module].push({
                name: methodName,
                module: method.module,
                api: method.api,
                doc: method.doc,
                model: modelId,
                signature: `def ${methodName}${method.signature}`,
                parameters: method.parameters,
                url: `/json/2/${modelId}/${methodName}`,
            });
        }

        const result = Object.values(modules).flatMap((methods) => methods);
        result.sort((a, b) => a.name.localeCompare(b.name));
        return result;
    }

    toggleAllModules(select) {
        this.state.modules.forEach((module) => (this.state.activeModules[module] = select));
    }
}
