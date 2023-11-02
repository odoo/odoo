/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { Component, onWillStart, onWillUpdateProps, useState } from "@odoo/owl";
import { Domain, InvalidDomainError } from "@web/core/domain";
import { DomainSelector } from "@web/core/domain_selector/domain_selector";
import { DomainSelectorDialog } from "@web/core/domain_selector_dialog/domain_selector_dialog";
import { EvaluationError } from "@web/core/py_js/py_builtin";
import { registry } from "@web/core/registry";
import { SelectCreateDialog } from "@web/views/view_dialogs/select_create_dialog";
import { standardFieldProps } from "../standard_field_props";
import { useBus, useService, useOwnedDialogs } from "@web/core/utils/hooks";
import {
    useGetDomainTreeDescription,
    useGetDefaultLeafDomain,
} from "@web/core/domain_selector/utils";
import { treeFromDomain } from "@web/core/tree_editor/condition_tree";

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
        isFoldable: { type: Boolean, optional: true },
    };
    static defaultProps = {
        editInDialog: false,
        isFoldable: false,
    };

    setup() {
        this.rpc = useService("rpc");
        this.orm = useService("orm");
        this.getDomainTreeDescription = useGetDomainTreeDescription();
        this.getDefaultLeafDomain = useGetDefaultLeafDomain();
        this.addDialog = useOwnedDialogs();

        this.state = useState({
            isValid: null,
            recordCount: null,
            folded: this.props.isFoldable,
            facets: [],
        });

        this.isDebugEdited = false;
        onWillStart(() => {
            this.checkProps(); // not awaited
            if (this.props.isFoldable) {
                this.loadFacets();
            }
        });
        onWillUpdateProps((nextProps) => {
            if (this.isDebugEdited) {
                this.quickValidityCheck(nextProps).then((isValid) => {
                    this.state.isValid = isValid;
                    this.isDebugEdited = false; // will allow the count to be loaded if needed
                    if (!isValid) {
                        this.state.recordCount = 0;
                        nextProps.record.setInvalidField(nextProps.name);
                    }
                });
            } else {
                this.checkProps(nextProps); // not awaited
            }
            if (nextProps.isFoldable) {
                this.loadFacets(nextProps);
            }
        });

        useBus(this.props.record.model.bus, "NEED_LOCAL_CHANGES", async (ev) => {
            if (this.isDebugEdited) {
                const props = this.props;
                ev.detail.proms.push(
                    this.quickValidityCheck(props).then((isValid) => {
                        if (isValid) {
                            this.isDebugEdited = false; // will allow the count to be loaded if needed
                        } else {
                            this.state.isValid = false;
                            this.state.recordCount = 0;
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

    async addCondition() {
        const defaultDomain = await this.getDefaultLeafDomain(this.getResModel());
        this.update(defaultDomain);
        this.state.folded = false;
    }

    async loadFacets(props = this.props) {
        const resModel = this.getResModel(props);

        if (!resModel) {
            this.state.facets = [];
            this.state.folded = false;
            return;
        }

        if (typeof resModel !== "string") {
            // we don't want to support invalid models
            throw new Error(`Invalid model: ${resModel}`);
        }

        let promises = [];
        const domain = this.getDomain(props);
        try {
            const tree = treeFromDomain(domain, { distributeNot: !this.env.debug });
            const trees = !tree.negate && tree.value === "&" ? tree.children : [tree];
            promises = trees.map(async (tree) => {
                const description = await this.getDomainTreeDescription(resModel, tree);
                return description;
            });
        } catch (error) {
            if (error.data?.name === "builtins.KeyError" && error.data.message === resModel) {
                // we don't want to support invalid models
                throw new Error(`Invalid model: ${resModel}`);
            }
            this.state.facets = [];
            this.state.folded = false;
        }
        this.state.facets = await Promise.all(promises);
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
                title: _t("Selected records"),
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

    async quickValidityCheck(props) {
        const resModel = this.getResModel(props);
        if (!resModel) {
            return false;
        }
        const domain = this.getEvaluatedDomain(props);
        if (domain.isInvalid) {
            return false;
        }
        return this.rpc("/web/domain/validate", { model: resModel, domain });
    }

    update(domain, isDebugEdited = false) {
        this.isDebugEdited = isDebugEdited;
        return this.props.record.update({ [this.props.name]: domain });
    }

    fold() {
        this.state.folded = true;
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
    displayName: _t("Domain"),
    supportedOptions: [
        {
            label: _t("Edit in dialog"),
            name: "in_dialog",
            type: "boolean",
        },
        {
            label: _t("Foldable"),
            name: "foldable",
            type: "boolean",
            help: _t("Display the domain using facets"),
        },
        {
            label: _t("Model"),
            name: "model",
            type: "string",
        },
    ],
    supportedTypes: ["char"],
    isEmpty: () => false,
    extractProps({ options }, dynamicInfo) {
        return {
            editInDialog: options.in_dialog,
            isFoldable: options.foldable,
            resModel: options.model,
            context: dynamicInfo.context,
        };
    },
};

registry.category("fields").add("domain", domainField);
