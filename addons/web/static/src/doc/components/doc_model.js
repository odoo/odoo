import { Component, useState, onWillUpdateProps, xml } from "@odoo/owl";
import { DocTable } from "@web/doc/components/doc_table";
import { getCrudMethodsExamples } from "@web/doc/utils/doc_model_utils";
import { DocMethod } from "@web/doc/components/doc_method";
import { useModelStore } from "@web/doc/utils/doc_model_store";
import { DocLoadingIndicator } from "@web/doc/components/doc_loading_indicator";

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

function move(index, arr, filterFn) {
    const fromIndex = arr.findIndex(filterFn);
    if (fromIndex > -1) {
        const element = arr[fromIndex];
        arr.splice(fromIndex, 1);
        arr.splice(index, 0, element);
    }
}

export class DocModel extends Component {
    static template = xml`
        <div class="o-doc-model position-relative flex flex-column p-3">
            <h1 class="w-100 mb-1 mt-2" t-out="this.state.model?.name ?? ''"></h1>
            <DocTable data="this.state.modelData"/>

            <h2 class="mt-3 mb-1" id="fields">Fields</h2>
            <DocLoadingIndicator
                isLoaded="this.state.model and this.state.model.fields != null"
                class="'o-fade-in'"
            >
                <DocTable data="this.fieldsData"/>
            </DocLoadingIndicator>

            <h2 class="mt-3 mb-1" id="methods">Methods</h2>
            <DocLoadingIndicator
                isLoaded="this.state.methods and this.state.methods.length > 0"
                class="'o-fade-in position-relative'"
            >
                <DocMethod
                    t-foreach="state.methods"
                    t-as="method"
                    t-key="method.model + '/' + method.name"
                    t-if="isModuleActive(method.module)"
                    method="method"
                />
            </DocLoadingIndicator>
            <div style="min-height: 30vh"/>
        </div>

        <aside class="o-doc-model-aside block position-sticky h-100 bg-0 overflow-auto pt-2 pb-2 ps-3 pe-3 border-start">
            <div
                class="flex w-100 cursor-pointer capitalize align-items-center"
                t-on-click="() => this.state.showModulesFilter = !this.state.showModulesFilter"
                role="button"
            >
                <div class="icon-btn ps-1" role="button" t-att-class="{ o_collapsed: !state.showModulesFilter}">
                    <i class="fa fa-angle-right" aria-hidden="true"></i>
                </div>
                <h2 class="ms-1">Modules</h2>
            </div>
            <t t-if="this.state.showModulesFilter">
                <span>
                    <a class="me-1" href="#" t-on-click="() => this.toggleAllModules(true)">
                        Select all
                    </a>
                    <a href="#" t-on-click="() => this.toggleAllModules(false)">
                        Deselect all
                    </a>
                </span>
                <div
                    t-foreach="state.modules"
                    t-as="module"
                    t-key="module"
                    class="flex align-items-center mb-1 cursor-pointer btn"
                    t-on-click="() => state.activeModules[module] = !state.activeModules[module]"
                >
                    <input class="me-1" type="checkbox" t-att-id="module" t-att-checked="state.activeModules[module]"/>
                    <label class="text-ellipsis" t-att-for="module" t-out="module" t-on-click.prevent=""></label>
                </div>
            </t>

            <h2>On This Page</h2>
            <a
                t-foreach="state.methods"
                t-as="method"
                t-key="method.model + '/' + method.name"
                t-out="method.name"
                t-if="isModuleActive(method.module)"
                t-att-href="'#' + method.name"
                class="block w-100 text-ellipsis"
            >
            </a>
        </aside>
    `;
    static components = {
        DocTable,
        DocMethod,
        DocLoadingIndicator,
    };
    static props = {
        modelId: true,
    };

    setup() {
        this.state = useState({
            model: undefined,
            modelData: { items: [] },
            crudMethods: [],
            methods: [],
            modules: [],
            activeModules: {
                core: true,
                base: true,
                web: true,
                crm: true,
            },
            showModulesFilter: true,
        });

        this.modelStore = useModelStore();
        this.updateModel(this.props.modelId);
        onWillUpdateProps((props) => this.updateModel(props.modelId));
    }

    get modelName() {
        return this.state.model?.name ?? "";
    }

    get fieldsData() {
        let fields = [];
        if (this.state.model && this.state.model.fields) {
            fields = Object.values(this.state.model.fields);
        }

        fields = fields
            .filter((fieldData) => this.isModuleActive(fieldData.module))
            .map((fieldData) => [
                { type: "code-like", value: fieldData.name },
                { type: "code-like", value: fieldData.type, class: getTypeColor(fieldData.type) },
                fieldData.string,
                {
                    type: "code-like",
                    value: fieldData.required ? "required" : "optional",
                    class: fieldData.required ? "text-red" : "text-muted",
                },
                {
                    type: "tooltip",
                    value: fieldData.help,
                },
                {
                    type: "code-like",
                    value: fieldData.module || "",
                },
            ]);

        fields.sort((a, b) => a[0].value.localeCompare(b[0].value));

        return {
            headers: ["Name", "Type", "Description", "Required", "Help", "Module"],
            items: fields,
        };
    }

    async updateModel(modelId) {
        const basicModel = this.modelStore.getBasicModelData(modelId);
        this.state.model = {
            model: modelId,
            name: basicModel.name,
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
            for (const fieldName in model.fields) {
                if (model.fields[fieldName].module) {
                    modules.add(model.fields[fieldName].module);
                }
            }
            for (const methodName in model.methods) {
                if (model.methods[methodName].module) {
                    modules.add(model.methods[methodName].module);
                }
            }
            modules = [...modules];
            modules.sort();
            move(0, modules, (m) => m === "core");
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
        });
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

        for (const module in modules) {
            modules[module].sort((a, b) => a.name.localeCompare(b.name));
        }

        const result = Object.values(modules).flatMap((methods) => methods);
        move(0, result, (m) => m.module === "core" && m.name === "search");
        move(1, result, (m) => m.module === "core" && m.name === "read");
        move(2, result, (m) => m.module === "core" && m.name === "create");
        move(3, result, (m) => m.module === "core" && m.name === "write");
        move(4, result, (m) => m.module === "core" && m.name === "unlink");
        return result;
    }

    toggleAllModules(select) {
        this.state.modules.forEach((module) => (this.state.activeModules[module] = select));
    }
}
