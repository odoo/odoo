import { Component, useState } from "@odoo/owl";
import { Domain, InvalidDomainError } from "@web/core/domain";
import { DomainSelector } from "@web/core/domain_selector/domain_selector";
import { useGetDefaultLeafDomain } from "@web/core/domain_selector/utils";
import { DomainSelectorDialog } from "@web/core/domain_selector_dialog/domain_selector_dialog";
import { _t } from "@web/core/l10n/translation";
import { rpc } from "@web/core/network/rpc";
import { EvaluationError } from "@web/core/py_js/py_builtin";
import { registry } from "@web/core/registry";
import { domainContainsExpressions } from "@web/core/tree_editor/domain_contains_expressions";
import { useBus, useOwnedDialogs, useService } from "@web/core/utils/hooks";
import { useRecordObserver } from "@web/model/relational_model/utils";
import { SelectCreateDialog } from "@web/views/view_dialogs/select_create_dialog";
import { standardFieldProps } from "../standard_field_props";

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
        countLimit: { type: Number, optional: true },
        allowExpressions: { type: Boolean, optional: true },
    };
    static defaultProps = {
        editInDialog: false,
        isFoldable: false,
        countLimit: 10000,
        allowExpressions: false,
    };

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.treeProcessor = useService("tree_processor");
        this.getDefaultLeafDomain = useGetDefaultLeafDomain();
        this.addDialog = useOwnedDialogs();

        this.state = useState({
            isValid: null,
            recordCount: null,
            hasLimitedCount: null,
            folded: this.props.isFoldable,
            facets: [],
        });

        this.debugDomain = null;
        useRecordObserver(async (record, nextProps) => {
            nextProps = { ...nextProps, record };
            if (this.debugDomain && this.props.readonly !== nextProps.readonly) {
                this.debugDomain = null;
            }
            if (this.debugDomain) {
                this.state.isValid = await this.quickValidityCheck(nextProps);
                if (!this.state.isValid) {
                    this.state.recordCount = 0;
                    nextProps.record.setInvalidField(nextProps.name);
                }
            } else {
                this.checkProps(nextProps); // not awaited
            }
            if (nextProps.isFoldable) {
                this.loadFacets(nextProps);
            }
        });

        useBus(this.props.record.model.bus, "NEED_LOCAL_CHANGES", async (ev) => {
            if (this.debugDomain) {
                const props = this.props;
                const handleChanges = async () => {
                    await props.record.update({ [props.name]: this.debugDomain });
                    const isValid = await this.quickValidityCheck(props);
                    if (isValid) {
                        this.debugDomain = null; // will allow the count to be loaded if needed
                    } else {
                        this.state.isValid = false;
                        this.state.recordCount = 0;
                        props.record.setInvalidField(props.name);
                    }
                };
                ev.detail.proms.push(handleChanges());
            }
        });
    }

    allowExpressions(props) {
        return props.allowExpressions;
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
        if (domainContainsExpressions(domainStringRepr)) {
            const allowExpressions = this.allowExpressions(props);
            if (domainStringRepr !== this.lastDomainChecked) {
                this.lastDomainChecked = domainStringRepr;
                this.notification.add(
                    allowExpressions
                        ? _t("The domain involves non-literals. Their evaluation might fail.")
                        : _t("The domain should not involve non-literals")
                );
            }
            if (!allowExpressions) {
                return { isInvalid: true };
            }
        }
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
            const tree = await this.treeProcessor.treeFromDomain(resModel, domain, !this.env.debug);
            const trees = !tree.negate && tree.value === "&" ? tree.children : [tree];
            promises = trees.map((tree) =>
                this.treeProcessor.getDomainTreeDescription(resModel, tree)
            );
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
            this.updateState({ isValid: false, recordCount: 0, hasLimitedCount: false });
            return;
        }

        let recordCount;
        let hasLimitedCount = false;
        const context = this.getContext(props);
        let limit;
        if (props.countLimit !== Number.MAX_SAFE_INTEGER) {
            limit = props.countLimit + 1;
        }
        try {
            recordCount = await this.orm.silent.searchCount(resModel, domain, { context, limit });
        } catch (error) {
            if (error.data?.name === "builtins.KeyError" && error.data.message === resModel) {
                // we don't want to support invalid models
                throw new Error(`Invalid model: ${resModel}`);
            }
            this.updateState({ isValid: false, recordCount: 0, hasLimitedCount: false });
            return;
        }
        if (limit && recordCount >= limit) {
            hasLimitedCount = true;
            recordCount = props.countLimit;
        }
        this.updateState({ isValid: true, recordCount, hasLimitedCount });
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
        return rpc("/web/domain/validate", { model: resModel, domain });
    }

    update(domain, isDebugEdited = false) {
        if (!isDebugEdited) {
            this.debugDomain = null;
        }
        this.props.record.update({ [this.props.name]: domain });
        this.props.record.model.bus.trigger("FIELD_IS_DIRTY", false);
    }

    debugUpdate(domain) {
        const isDirty = domain !== this.getDomain();
        this.debugDomain = isDirty ? domain : null;
        this.props.record.model.bus.trigger("FIELD_IS_DIRTY", isDirty);
        if (!this.props.record.isValid) {
            this.props.record.resetFieldValidity(this.props.name);
        }
    }

    fold() {
        this.state.folded = true;
    }

    updateState(params = {}) {
        Object.assign(this.state, {
            isValid: "isValid" in params ? params.isValid : null,
            recordCount: "recordCount" in params ? params.recordCount : null,
            hasLimitedCount: "hasLimitedCount" in params ? params.hasLimitedCount : null,
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
            label: _t("Allow expressions"),
            name: "allow_expressions",
            type: "boolean",
            help: _t("If true, non-literals are accepted"),
        },
        {
            label: _t("Model"),
            name: "model",
            type: "string",
        },
        {
            label: _t("Count Limit"),
            name: "count_limit",
            type: "number",
        },
    ],
    supportedTypes: ["char", "text"],
    isEmpty: () => false,
    extractProps({ options }, dynamicInfo) {
        return {
            editInDialog: options.in_dialog,
            isFoldable: options.foldable,
            allowExpressions: options.allow_expressions,
            resModel: options.model,
            countLimit: options.count_limit,
            context: dynamicInfo.context,
        };
    },
};

registry.category("fields").add("domain", domainField);
