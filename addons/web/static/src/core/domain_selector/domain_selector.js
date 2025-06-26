import { Component, onWillStart, onWillUpdateProps } from "@odoo/owl";
import { CheckBox } from "@web/core/checkbox/checkbox";
import { Domain } from "@web/core/domain";
import { getDomainDisplayedOperators } from "@web/core/domain_selector/domain_selector_operator_editor";
import { _t } from "@web/core/l10n/translation";
import { ModelFieldSelector } from "@web/core/model_field_selector/model_field_selector";
import { condition, formatValue } from "@web/core/tree_editor/condition_tree";
import { constructTreeFromDomain } from "@web/core/tree_editor/construct_tree_from_domain";
import { domainFromTree } from "@web/core/tree_editor/domain_from_tree";
import { TreeEditor } from "@web/core/tree_editor/tree_editor";
import { getOperatorEditorInfo } from "@web/core/tree_editor/tree_editor_operator_editor";
import { treeFromDomain } from "@web/core/tree_editor/tree_from_domain";
import { useMakeGetFieldDef } from "@web/core/tree_editor/utils";
import { useService } from "@web/core/utils/hooks";
import { deepEqual } from "@web/core/utils/objects";
import { getDefaultCondition } from "./utils";

const ARCHIVED_CONDITION = condition("active", "in", [true, false]);
const ARCHIVED_DOMAIN = `[("active", "in", [True, False])]`;

export class DomainSelector extends Component {
    static template = "web.DomainSelector";
    static components = { TreeEditor, CheckBox };
    static props = {
        domain: String,
        resModel: String,
        className: { type: String, optional: true },
        defaultConnector: { type: [{ value: "&" }, { value: "|" }], optional: true },
        isDebugMode: { type: Boolean, optional: true },
        allowExpressions: { type: Boolean, optional: true },
        readonly: { type: Boolean, optional: true },
        update: { type: Function, optional: true },
        debugUpdate: { type: Function, optional: true },
    };
    static defaultProps = {
        isDebugMode: false,
        allowExpressions: true,
        readonly: true,
        update: () => {},
    };

    setup() {
        this.fieldService = useService("field");
        this.makeGetFieldDef = useMakeGetFieldDef(this.fieldService);

        this.tree = null;
        this.showArchivedCheckbox = false;
        this.includeArchived = false;

        onWillStart(() => this.onPropsUpdated(this.props));
        onWillUpdateProps((np) => this.onPropsUpdated(np));
    }

    async onPropsUpdated(p) {
        let domain;
        let isSupported = true;
        try {
            domain = new Domain(p.domain);
        } catch {
            isSupported = false;
        }
        if (!isSupported) {
            this.tree = null;
            this.showArchivedCheckbox = false;
            this.includeArchived = false;
            return;
        }

        const getFieldDef = await this.makeGetFieldDef(
            p.resModel,
            constructTreeFromDomain(domain),
            ["active"]
        );

        this.tree = treeFromDomain(domain, {
            getFieldDef,
            distributeNot: !p.isDebugMode,
        });

        this.showArchivedCheckbox = this.getShowArchivedCheckBox(Boolean(getFieldDef("active")), p);
        this.includeArchived = false;
        if (this.showArchivedCheckbox) {
            if (this.tree.value === "&") {
                this.tree.children = this.tree.children.filter((child) => {
                    if (deepEqual(child, ARCHIVED_CONDITION)) {
                        this.includeArchived = true;
                        return false;
                    }
                    return true;
                });
                if (this.tree.children.length === 1) {
                    this.tree = this.tree.children[0];
                }
            } else if (deepEqual(this.tree, ARCHIVED_CONDITION)) {
                this.includeArchived = true;
                this.tree = treeFromDomain(`[]`);
            }
        }
    }

    getShowArchivedCheckBox(hasActiveField, props) {
        return hasActiveField;
    }

    getDefaultCondition(fieldDefs) {
        return getDefaultCondition(fieldDefs);
    }

    getDefaultOperator(fieldDef) {
        return getDomainDisplayedOperators(fieldDef, {
            allowExpressions: this.props.allowExpressions,
        })[0];
    }

    getOperatorEditorInfo(fieldDef) {
        const operators = getDomainDisplayedOperators(fieldDef, {
            allowExpressions: this.props.allowExpressions,
        });
        return getOperatorEditorInfo(operators, fieldDef);
    }

    getPathEditorInfo(resModel, defaultCondition) {
        const { isDebugMode } = this.props;
        return {
            component: ModelFieldSelector,
            extractProps: ({ update, value: path }) => ({
                path,
                update,
                resModel,
                isDebugMode,
                readonly: false,
            }),
            isSupported: (path) => [0, 1].includes(path) || typeof path === "string",
            defaultValue: () => defaultCondition.path,
            stringify: (path) => formatValue(path),
            message: _t("Invalid field chain"),
        };
    }

    toggleIncludeArchived() {
        this.includeArchived = !this.includeArchived;
        this.update(this.tree);
    }

    resetDomain() {
        this.props.update("[]");
    }

    onDomainInput(domain) {
        if (this.props.debugUpdate) {
            this.props.debugUpdate(domain);
        }
    }

    onDomainChange(domain) {
        this.props.update(domain, true);
    }
    update(tree) {
        const archiveDomain = this.includeArchived ? ARCHIVED_DOMAIN : `[]`;
        const domain = tree
            ? Domain.and([domainFromTree(tree), archiveDomain]).toString()
            : archiveDomain;
        this.props.update(domain);
    }
}
