// @ts-check
/** @odoo-module native */

import { onWillDestroy, useState } from "@odoo/owl";
import { DomainSelector } from "@web/components/domain_selector/domain_selector";
import { useGetDefaultLeafDomain } from "@web/components/domain_selector/utils";
import { DomainSelectorDialog } from "@web/components/domain_selector_dialog/domain_selector_dialog";
import { Domain, InvalidDomainError } from "@web/core/domain";
import { rpc } from "@web/core/network/rpc";
import { getSelectCreateDialog } from "@web/core/record_dialog_port";
import { _t } from "@web/core/translation";
import { domainContainsExpressions } from "@web/core/tree/domain_contains_expressions";
import { KeepLast, SupersededError } from "@web/core/utils/concurrency";
import { useOwnedDialogs, useService } from "@web/core/utils/hooks";
import { registerField } from "@web/fields/_registry";
import { FieldComponent } from "@web/fields/field_component";
import { useFieldDirtySignal } from "@web/fields/field_dirty_signal";
import { useFieldFlush } from "@web/fields/hooks/debounced_field_commit";
import { useRecordObserver } from "@web/fields/hooks/record_observer";
import { standardFieldProps } from "@web/fields/standard_field_props";

export class DomainField extends FieldComponent {
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

        this.keepLastCount = new KeepLast({ rejectSuperseded: true });
        this.keepLastFacets = new KeepLast({ rejectSuperseded: true });
        onWillDestroy(() => {
            this.keepLastCount.cancel();
            this.keepLastFacets.cancel();
        });

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
                this.checkProps(nextProps);
            }
            if (nextProps.isFoldable) {
                this.loadFacets(nextProps);
            }
        });

        const flushDebugDomain = (ev) => {
            if (!this.debugDomain) {
                return;
            }
            const props = this.props;
            const handleChanges = async () => {
                await props.record.update({
                    [props.name]: this.debugDomain,
                });
                const isValid = await this.quickValidityCheck(props);
                if (isValid) {
                    this.debugDomain = null;
                } else {
                    this.state.isValid = false;
                    this.state.recordCount = 0;
                    props.record.setInvalidField(props.name);
                }
            };
            ev.detail?.proms?.push(handleChanges());
        };
        useFieldFlush(this.props.record.model.bus, flushDebugDomain);

        this.setFieldDirty = useFieldDirtySignal();
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

    /**
     * @param {Object} [props]
     * @returns {{ domain: any[] | { isInvalid: true }, hasExpressions: boolean }}
     */
    evaluateDomain(props = this.props) {
        const domainStringRepr = this.getDomain(props);
        const evalContext = this.getContext(props);
        const hasExpressions = domainContainsExpressions(domainStringRepr);
        if (hasExpressions && !this.allowExpressions(props)) {
            return { domain: { isInvalid: true }, hasExpressions };
        }
        try {
            return {
                domain: new Domain(domainStringRepr).toList(evalContext),
                hasExpressions,
            };
        } catch (error) {
            if (error instanceof InvalidDomainError) {
                return { domain: { isInvalid: true }, hasExpressions };
            }
            throw error;
        }
    }

    /** @param {Object} [props] */
    reportDomainExpressions(props = this.props) {
        const domainStringRepr = this.getDomain(props);
        if (
            !domainContainsExpressions(domainStringRepr) ||
            domainStringRepr === this.lastDomainChecked
        ) {
            return;
        }
        this.lastDomainChecked = domainStringRepr;
        this.notification.add(
            this.allowExpressions(props)
                ? _t("The domain involves non-literals. Their evaluation might fail.")
                : _t("The domain should not involve non-literals"),
        );
    }

    /**
     * @param {Object} [props]
     * @returns {any[] | { isInvalid: true }}
     */
    getEvaluatedDomain(props = this.props) {
        this.reportDomainExpressions(props);
        return this.evaluateDomain(props).domain;
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
        this.keepLastFacets.cancel();
        const resModel = this.getResModel(props);

        if (!resModel || typeof resModel !== "string") {
            this.state.facets = [];
            this.state.folded = false;
            return;
        }

        const domain = this.getDomain(props);
        let facets;
        try {
            facets = await this.keepLastFacets.add(
                (async () => {
                    const tree = await this.treeProcessor.treeFromDomain(
                        resModel,
                        domain,
                        !this.env.debug,
                    );
                    const castTree = /** @type {any} */ (tree);
                    const trees =
                        !castTree.negate && tree.value === "&"
                            ? castTree.children
                            : [tree];
                    return Promise.all(
                        trees.map((tree) =>
                            this.treeProcessor.getDomainTreeDescription(resModel, tree),
                        ),
                    );
                })(),
            );
        } catch (error) {
            if (error instanceof SupersededError) {
                return;
            }
            this.state.facets = [];
            this.state.folded = false;
            return;
        }
        this.state.facets = facets;
    }

    async checkProps(props = this.props) {
        this.keepLastCount.cancel();
        const resModel = this.getResModel(props);
        if (!resModel) {
            this.updateState({});
            return;
        }

        if (typeof resModel !== "string") {
            this.updateState({
                isValid: false,
                recordCount: 0,
                hasLimitedCount: false,
            });
            return;
        }

        const domain = this.getEvaluatedDomain(props);
        if (/** @type {any} */ (domain).isInvalid) {
            this.updateState({
                isValid: false,
                recordCount: 0,
                hasLimitedCount: false,
            });
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
            recordCount = await this.keepLastCount.add(
                this.orm.silent.searchCount(resModel, /** @type {any} */ (domain), {
                    context,
                    limit,
                }),
            );
        } catch (error) {
            if (error instanceof SupersededError) {
                return;
            }
            this.updateState({
                isValid: false,
                recordCount: 0,
                hasLimitedCount: false,
            });
            return;
        }
        if (limit && recordCount >= limit) {
            hasLimitedCount = true;
            recordCount = props.countLimit;
        }
        this.updateState({ isValid: true, recordCount, hasLimitedCount });
    }

    onButtonClick() {
        const SelectCreateDialog = getSelectCreateDialog();
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
                onClose: () => this.checkProps(),
            },
        );
    }

    onEditDialogBtnClick() {
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
        if (/** @type {any} */ (domain).isInvalid) {
            return false;
        }
        return rpc("/web/domain/validate", { model: resModel, domain });
    }

    /** @param {boolean} isDirty */
    _setIsDirty(isDirty) {
        this.setFieldDirty(isDirty);
    }

    update(domain, isDebugEdited = false) {
        if (!isDebugEdited) {
            this.debugDomain = null;
        }
        this.field.update(domain);
        this._setIsDirty(false);
    }

    debugUpdate(domain) {
        const isDirty = domain !== this.getDomain();
        this.debugDomain = isDirty ? domain : null;
        this._setIsDirty(isDirty);
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
            hasLimitedCount:
                "hasLimitedCount" in params ? params.hasLimitedCount : null,
        });
    }
}

/** @type {import("registries").FieldsRegistryItemShape} */
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

registerField("domain", domainField);
