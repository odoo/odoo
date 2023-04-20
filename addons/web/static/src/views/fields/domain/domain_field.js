/** @odoo-module **/

import { _lt } from "@web/core/l10n/translation";
import { Component, onWillStart, onWillUpdateProps, useState } from "@odoo/owl";
import { Domain, InvalidDomainError } from "@web/core/domain";
import { DomainSelector } from "@web/core/domain_selector/domain_selector";
import { DomainSelectorDialog } from "@web/core/domain_selector_dialog/domain_selector_dialog";
import { EvaluationError } from "@web/core/py_js/py_interpreter";
import { registry } from "@web/core/registry";
import { SelectCreateDialog } from "@web/views/view_dialogs/select_create_dialog";
import { standardFieldProps } from "../standard_field_props";
import { useBus, useService, useOwnedDialogs } from "@web/core/utils/hooks";

export class DomainField extends Component {
    static template = "web.DomainField";
    static components = {
        DomainSelector,
    };
    static props = {
        ...standardFieldProps,
        context: { type: Object, optional: true },
        editInDialog: { type: Boolean, optional: true },
        resModel: { type: String, optional: true },
    };
    static defaultProps = {
        editInDialog: false,
    };

    setup() {
        this.orm = useService("orm");
        this.addDialog = useOwnedDialogs();

        this.state = useState({
            isValid: null,
            recordCount: null,
        });

        this.isDebugEdited = false;
        onWillStart(() => {
            this.checkProps(); // not awaited
        });
        onWillUpdateProps((nextProps) => {
            this.isDebugEdited = this.isDebugEdited && this.props.readonly === nextProps.readonly;
            if (!this.isDebugEdited) {
                this.checkProps(nextProps); // not awaited
            }
        });

        useBus(this.props.record.model.bus, "NEED_LOCAL_CHANGES", async (ev) => {
            if (this.isDebugEdited) {
                const props = this.props;
                ev.detail.proms.push(
                    this.checkProps(props).then(() => {
                        if (!this.state.isValid) {
                            props.record.setInvalidField(props.name);
                        }
                    })
                );
            }
        });
    }

    getContext(props = this.props) {
        return props.context;
    }

    getDomain(props = this.props) {
        return props.record.data[props.name] || "[]";
    }

    getEvaluatedDomain(props = this.props) {
        const domainStringRepr = this.getDomain(props);
        const evalContext = this.getContext(props);
        try {
            const domain = new Domain(domainStringRepr).toList(evalContext);
            // Here, there is still some incertitude on the domain validity.
            // we could improve this check but a complete (async) check is done
            // when loading the record count associated with the domain.
            return domain;
        } catch (error) {
            if (error instanceof InvalidDomainError || error instanceof EvaluationError) {
                return { isInvalid: true };
            }
            throw error;
        }
    }

    getResModel(props = this.props) {
        let resModel = props.resModel;
        if (props.record.fieldNames.includes(resModel)) {
            resModel = props.record.data[resModel];
        }
        return resModel;
    }

    async checkProps(props = this.props) {
        const resModel = this.getResModel(props);
        if (!resModel) {
            this.updateState({});
            return;
        }

        if (typeof resModel !== "string") {
            // we don't want to support invalid models
            throw new Error(`Invalid model: ${resModel}`);
        }

        const domain = this.getEvaluatedDomain(props);
        if (domain.isInvalid) {
            this.updateState({ isValid: false, recordCount: 0 });
            return;
        }

        let recordCount;
        const context = this.getContext(props);
        try {
            recordCount = await this.orm.silent.searchCount(resModel, domain, { context });
        } catch (error) {
            if (error.data?.name === "builtins.KeyError" && error.data.message === resModel) {
                // we don't want to support invalid models
                throw new Error(`Invalid model: ${resModel}`);
            }
            this.updateState({ isValid: false, recordCount: 0 });
            return;
        }

        this.updateState({ isValid: true, recordCount });
    }

    onButtonClick() {
        // resModel, domain, and context are assumed to be valid here.
        this.addDialog(
            SelectCreateDialog,
            {
                title: this.env._t("Selected records"),
                noCreate: true,
                multiSelect: false,
                resModel: this.getResModel(),
                domain: this.getEvaluatedDomain(),
                context: this.getContext(),
            },
            {
                // The counter is reloaded "on close" because some modal allows
                // to modify data that can impact the counter
                onClose: () => this.checkProps(),
            }
        );
    }

    onEditDialogBtnClick() {
        // resModel is assumed to be valid here
        this.addDialog(DomainSelectorDialog, {
            resModel: this.getResModel(),
            domain: this.getDomain(),
            isDebugMode: !!this.env.debug,
            onConfirm: this.update.bind(this),
        });
    }

    update(domain, isDebugEdited = false) {
        this.isDebugEdited = isDebugEdited;
        return this.props.record.update({ [this.props.name]: domain });
    }

    updateState(params = {}) {
        Object.assign(this.state, {
            isValid: "isValid" in params ? params.isValid : null,
            recordCount: "recordCount" in params ? params.recordCount : null,
        });
    }
}

export const domainField = {
    component: DomainField,
    displayName: _lt("Domain"),
    supportedOptions: [
        {
            label: _lt("Edit in dialog"),
            name: "in_dialog",
            type: "boolean",
        },
        {
            label: _lt("Model"),
            name: "model",
            type: "string",
        },
    ],
    supportedTypes: ["char"],
    isEmpty: () => false,
    extractProps({ options }, dynamicInfo) {
        return {
            editInDialog: options.in_dialog,
            resModel: options.model,
            context: dynamicInfo.context,
        };
    },
};

registry.category("fields").add("domain", domainField);
