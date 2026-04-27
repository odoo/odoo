/** @odoo-module */
import { Component, useState, xml } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { ModelFieldSelector } from "@web/core/model_field_selector/model_field_selector";
import { useDialogConfirmation } from "@web_studio/client_action/utils";
import { useOwnedDialogs, useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { DomainSelector } from "@web/core/domain_selector/domain_selector";
import { SelectionContentDialog } from "@web_studio/client_action/view_editor/interactive_editor/field_configuration/selection_content_dialog";
import { RecordSelector } from "@web/core/record_selectors/record_selector";

export class SelectionValuesEditor extends Component {
    static components = {
        SelectionContentDialog,
    };
    static props = {
        configurationModel: { type: Object },
        confirm: { type: Function },
        cancel: { type: Function },
    };
    static template = "web_studio.SelectionValuesEditor";
    static Model = class SelectionValuesModel {
        constructor() {
            this.selection = "[]";
        }
        get isValid() {
            return true;
        }
    };
    get selection() {
        return JSON.parse(this.props.configurationModel.selection);
    }
    onConfirm(choices) {
        this.props.configurationModel.selection = JSON.stringify(choices);
        this.props.confirm();
    }
}

export class RelationalFieldConfigurator extends Component {
    static template = "web_studio.RelationalFieldConfigurator";
    static components = { RecordSelector };
    static props = {
        configurationModel: { type: Object },
        resModel: { type: String },
        fieldType: { type: String },
    };
    static Model = class RelationalFieldModel {
        constructor() {
            this.relationId = false;
        }
        get isValid() {
            return !!this.relationId;
        }
    };

    setup() {
        this.state = useState(this.props.configurationModel);
    }

    get valueSelectorProps() {
        if (this.props.fieldType === "one2many") {
            return {
                resModel: "ir.model.fields",
                domain: [
                    ["relation", "=", this.props.resModel],
                    ["ttype", "=", "many2one"],
                    ["model_id.abstract", "=", false],
                    ["store", "=", true],
                ],
                resId: this.state.relationId,
                update: (resId) => {
                    this.state.relationId = resId;
                },
            };
        }
        return {
            resModel: "ir.model",
            domain: [
                ["transient", "=", false],
                ["abstract", "=", false],
                ["model", "not in", ["knowledge.article"]],
            ],
            resId: this.state.relationId,
            update: (resId) => {
                this.state.relationId = resId;
            },
        };
    }
}

class RelatedChainBuilderModel {
    static services = ["field", "dialog"];

    constructor({ services, props }) {
        this.services = services;
        this.relatedParams = {};
        this.fieldInfo = { resModel: props.resModel, fieldDef: null };
        this.resModel = props.resModel;
    }

    get isValid() {
        return !!this.relatedParams.related;
    }

    getRelatedFieldDescription(resModel, lastField) {
        const fieldType = lastField.type;
        const relatedDescription = {
            readonly: true,
            copy: false,
            string: lastField.string,
            type: fieldType,
            store: false,
        };

        if (["many2one", "many2many", "one2many"].includes(fieldType)) {
            relatedDescription.relation = lastField.relation;
        }
        if (["one2many", "many2many"].includes(fieldType)) {
            relatedDescription.relational_model = resModel;
        }
        if (fieldType === "selection") {
            relatedDescription.selection = lastField.selection;
        }
        return relatedDescription;
    }

    async confirm() {
        const relatedDescription = this.getRelatedFieldDescription(
            this.fieldInfo.resModel,
            this.fieldInfo.fieldDef
        );
        Object.assign(this.relatedParams, relatedDescription);
        return true;
    }
}

export class RelatedChainBuilder extends Component {
    static template = xml`<ModelFieldSelector resModel="props.resModel" path="fieldChain" readonly="false" filter.bind="filter" update.bind="updateChain" />`;
    static components = { ModelFieldSelector };
    static props = {
        resModel: { type: String },
        configurationModel: { type: Object },
    };
    static Model = RelatedChainBuilderModel;

    setup() {
        this.state = useState(this.props.configurationModel);
        this.relatedParams.related = "";
    }

    get relatedParams() {
        return this.state.relatedParams;
    }

    get fieldChain() {
        return this.relatedParams.related;
    }

    filter(fieldDef, path) {
        return fieldDef.type !== "properties";
    }

    async updateChain(path, fieldInfo) {
        this.relatedParams.related = path;
        this.state.fieldInfo = fieldInfo;
    }
}

function useConfiguratorModel(Model, props) {
    const services = Object.fromEntries(
        (Model.services || []).map((servName) => {
            let serv;
            if (servName === "dialog") {
                serv = { add: useOwnedDialogs() };
            } else {
                serv = useService(servName);
            }
            return [servName, serv];
        })
    );

    const model = new Model({ services, props });
    return useState(model);
}

export class FieldConfigurationDialog extends Component {
    static props = {
        confirm: { type: Function },
        cancel: { type: Function },
        close: { type: Function },
        Component: { type: Function },
        componentProps: { type: Object, optional: true },
        fieldType: { type: String, optional: true },
        isDialog: { type: Boolean, optional: true },
        title: { type: String, optional: true },
        size: { type: String, optional: true },
    };
    static template = "web_studio.FieldConfigurationDialog";
    static components = { Dialog };

    setup() {
        const { confirm, cancel } = useDialogConfirmation({
            confirm: async () => {
                let confirmValues = false;
                if (!this.configurationModel.isValid) {
                    return false;
                }
                if (this.configurationModel.confirm) {
                    const res = await this.configurationModel.confirm();
                    if (res || res === undefined) {
                        confirmValues = this.configurationModel;
                    }
                } else {
                    confirmValues = this.configurationModel;
                }
                return this.props.confirm(confirmValues);
            },
            cancel: () => this.props.cancel(),
        });
        this.confirm = confirm;
        this.cancel = cancel;
        this.configurationModel = useConfiguratorModel(
            this.Component.Model,
            this.props.componentProps
        );
    }

    get title() {
        if (this.props.title) {
            return this.props.title;
        }
        if (this.props.fieldType) {
            return _t("Field properties: %s", this.props.fieldType);
        }
        return "";
    }

    get Component() {
        return this.props.Component;
    }

    get canConfirm() {
        return this.configurationModel.isValid;
    }
}

export class FilterConfiguration extends Component {
    static components = { DomainSelector };
    static template = "web_studio.FilterConfiguration";
    static props = {
        resModel: { type: String },
        configurationModel: { type: Object },
    };
    static Model = class FilterConfigurationModel {
        constructor() {
            this.filterLabel = "";
            this.domain = "[]";
        }

        get isValid() {
            return !!this.filterLabel;
        }
    };

    setup() {
        this.state = useState(this.props.configurationModel);
    }

    get domainSelectorProps() {
        return {
            resModel: this.props.resModel,
            readonly: false,
            domain: this.state.domain,
            update: (domainStr) => {
                this.state.domain = domainStr;
            },
            isDebugMode: !!this.env.debug,
        };
    }
}
