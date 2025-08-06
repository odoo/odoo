import { Component, useState, useEffect, onPatched, markup } from "@odoo/owl";
import { DocTable, TABLE_TYPES } from "@api_doc/components/doc_table";
import { getCrudMethodsExamples } from "@api_doc/utils/doc_model_utils";
import { DocMethod } from "@api_doc/components/doc_method";
import { DocLoadingIndicator } from "@api_doc/components/doc_loading_indicator";
import { useDocUI } from "@api_doc/utils/doc_ui_store";

const TYPE_COLORS = {
    "text-success": ["integer", "char", "boolean", "selection", "float"],
    "text-info": ["html", "datetime", "date", "binary"],
    "text-warning": ["many2one", "many2many", "one2many", "many2one_reference"],
};

function getTypeColor(type) {
    for (const key in TYPE_COLORS) {
        if (TYPE_COLORS[key].includes(type)) {
            return key;
        }
    }
}

function getTypeData(fieldData) {
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
            fields: { data: { items: [] }},
            modules: [],
            activeModules: {
                core: true,
                base: false,
            },
            showModulesFilter: true,
        });

        this.ui = useDocUI();
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
            ],
        );

        let lastFocusedElement = null
        onPatched(
            () => {
                let el = null;
                if (this.modelStore.activeMethod) {
                    el = document.getElementById(this.modelStore.activeMethod);
                }
                if (this.modelStore.activeField) {
                    el = document.getElementById(this.modelStore.activeField);
                }
                if (el && el != lastFocusedElement) {
                    lastFocusedElement = el;
                    el.scrollIntoView({ behavior: "smooth" });
                }
            }
        );
    }

    get modelName() {
        return this.state.model?.name ?? "";
    }

    async update() {
        if (!this.state.model || this.state.model.model !== this.modelStore.activeModel.model) {
            this.updateModel(this.modelStore.activeModel);
        }

        this.updateActives();
    }

    updateModel(model) {
        const modelId = model.model;

        this.state.model = {
            model: modelId,
            name: model.name,
            doc: "",
            fields: null,
            error: null,
        };
        this.state.modelData = { items: [] };
        this.state.methods = [];
        this.state.modules = [];

        this.modelStore.loadModel(modelId)
            .then((model) => {
                if (this.state.model.model !== model.model) {
                    return;
                }

                this.state.model = model;
                this.state.modelData = {
                    items: [
                        ["Model Name", { type: "code", value: model.model }],
                        ...(model.doc ? [["Description", model.doc]] : []),
                    ]
                };

                this.updateModules();
                this.updateMethods();
                this.updateFields();

                const crudExamples = getCrudMethodsExamples(model);
                for (const method of this.state.methods) {
                    if (method.name in crudExamples) {
                        method.request = crudExamples[method.name].request;
                        method.responseCode = crudExamples[method.name].responseCode;
                    }
                }
                this.updateActives();
            })
            .catch((error) => {
                console.error(error);
                this.state.error = error;
            });
    }

    isModuleActive(module) {
        return !module || this.state.activeModules[module];
    }

    updateModules() {
        const model = this.state.model;
        let modules = new Set();
        Object.values(model.fields).forEach((f) => f.module && modules.add(f.module));
        Object.values(model.methods).forEach((m) => m.module && modules.add(m.module));

        modules = [...modules];
        modules.sort((a, b) => (a === "core" ? -1 : b === "core" ? 1 : a.localeCompare(b)));
        this.state.modules = modules;
    }

    updateMethods() {
        const model = this.state.model;
        const methods = [];

        for (const methodName in model.methods) {
            const method = model.methods[methodName];

            let returnDoc = "";
            let returnAnnotation = "";
            if (method.return) {
                returnDoc = method.return.doc ? markup(method.return.doc) : "";
                returnAnnotation = method.return.annotation;
            }

            methods.push({
                name: methodName,
                module: method.module,
                api: method.api,
                doc: method.doc,
                model: model.model,
                parameters: method.parameters,
                url: `/json/2/${model.model}/${methodName}`,
                returnDoc: returnDoc,
                returnAnnotation: returnAnnotation,
            });
        }

        const crudOrder = ["search_read", "search", "read", "create", "write", "unlink"];
        methods.sort((a, b) => {
            const aIndex = crudOrder.indexOf(a.name);
            const bIndex = crudOrder.indexOf(b.name);
            if (aIndex >= 0 && bIndex >= 0) {
                return aIndex - bIndex;
            } else if (aIndex >= 0) {
                return -1;
            } else if (bIndex >= 0) {
                return 1;
            }
            return a.name.localeCompare(b.name)
        });
        this.state.methods = methods;
    }

    updateFields() {
        const model = this.state.model;
        let fields = [];
        let activeIndex = -1;

        if (model && model.fields) {
            fields = Object.values(model.fields);
        }

        fields = fields
            .filter((fieldData) => this.isModuleActive(fieldData.module))
            .map((fieldData, index) => {
                if (fieldData.name === this.modelStore.activeField) {
                    activeIndex = index
                }
                return [
                    { type: TABLE_TYPES.Code, value: fieldData.name },
                    getTypeData(fieldData),
                    fieldData.string,
                    {
                        type: TABLE_TYPES.Code,
                        value: fieldData.required ? "required" : "optional",
                        class: fieldData.required ? "text-danger" : "text-muted",
                    },
                    {
                        type: TABLE_TYPES.Tooltip,
                        value: fieldData.help,
                    },
                    {
                        type: TABLE_TYPES.Code,
                        value: fieldData.module || "",
                    },
                ]
            });

        fields.sort((a, b) => a[0].value.localeCompare(b[0].value));

        this.state.fields = {
            activeIndex,
            data: {
                headers: ["Name", "Type", "Description", "Required", "Help", "Module"],
                items: fields,
            },
        };
    }

    async updateActives() {
        const method = this.state.model.methods?.[this.modelStore.activeMethod];
        const activeModules = [];
        if (method) {
            activeModules.push(method.module);
        }

        const fieldData = this.state.model.fields?.[this.modelStore.activeField];
        if (fieldData) {
            activeModules.push(fieldData.module);
        }

        this.setActiveModules(activeModules, true);
    }

    setActiveModules(modules, active) {
        for (const module of modules) {
            this.state.activeModules[module] = active;
        }
        this.updateFields();
    }

    toggleAllModules(select) {
        this.setActiveModules(this.state.modules, select);
    }
}
