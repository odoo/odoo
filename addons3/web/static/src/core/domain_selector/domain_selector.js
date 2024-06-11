/** @odoo-module **/

import { extractPathsFromDomain, useGetDefaultCondition } from "@web/core/domain_selector/utils";
import { Component, onWillStart, onWillUpdateProps } from "@odoo/owl";
import { Domain } from "@web/core/domain";
import { TreeEditor } from "@web/core/tree_editor/tree_editor";
import {
    domainFromTree,
    treeFromDomain,
    formatValue,
    condition,
} from "@web/core/tree_editor/condition_tree";
import { useLoadFieldInfo } from "@web/core/model_field_selector/utils";
import { CheckBox } from "@web/core/checkbox/checkbox";
import { deepEqual } from "@web/core/utils/objects";
import { getDomainDisplayedOperators } from "@web/core/domain_selector/domain_selector_operator_editor";
import { getOperatorEditorInfo } from "@web/core/tree_editor/tree_editor_operator_editor";
import { _t } from "@web/core/l10n/translation";
import { ModelFieldSelector } from "@web/core/model_field_selector/model_field_selector";

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
        readonly: { type: Boolean, optional: true },
        update: { type: Function, optional: true },
    };
    static defaultProps = {
        isDebugMode: false,
        readonly: true,
        update: () => {},
    };

    setup() {
        this.loadFieldInfo = useLoadFieldInfo();
        this.getDefaultCondition = useGetDefaultCondition();

        this.tree = null;
        this.defaultCondition = null;
        this.fieldDefs = {};
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
            this.defaultCondition = null;
            this.fieldDefs = {};
            this.showArchivedCheckbox = false;
            this.includeArchived = false;
            return;
        }

        const paths = new Set([...extractPathsFromDomain(domain), "active"]);
        await this.loadFieldDefs(p.resModel, paths);

        const [defaultCondition] = await Promise.all([
            this.getDefaultCondition(p.resModel),
            this.loadFieldDefs(p.resModel, paths),
        ]);

        this.tree = treeFromDomain(domain, {
            getFieldDef: this.getFieldDef.bind(this),
            distributeNot: !p.isDebugMode,
        });
        this.defaultCondition = defaultCondition;

        this.showArchivedCheckbox = Boolean(this.fieldDefs.active);
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

    getFieldDef(path) {
        if (typeof path === "string") {
            return this.fieldDefs[path];
        }
        return null;
    }

    getDefaultOperator(fieldDef) {
        return getDomainDisplayedOperators(fieldDef)[0];
    }

    getOperatorEditorInfo(node) {
        const fieldDef = this.getFieldDef(node.path);
        const operators = getDomainDisplayedOperators(fieldDef);
        return getOperatorEditorInfo(operators);
    }

    getPathEditorInfo() {
        const { resModel, isDebugMode } = this.props;
        return {
            component: ModelFieldSelector,
            extractProps: ({ update, value: path }) => {
                return {
                    path,
                    update,
                    resModel,
                    isDebugMode,
                    readonly: false,
                };
            },
            isSupported: (path) => [0, 1].includes(path) || typeof path === "string",
            defaultValue: () => "id",
            stringify: (path) => formatValue(path),
            message: _t("Invalid field chain"),
        };
    }

    async loadFieldDefs(resModel, paths) {
        const promises = [];
        const fieldDefs = {};
        for (const path of paths) {
            if (typeof path === "string") {
                promises.push(
                    this.loadFieldInfo(resModel, path).then(({ fieldDef }) => {
                        fieldDefs[path] = fieldDef;
                    })
                );
            }
        }
        await Promise.all(promises);
        this.fieldDefs = fieldDefs;
    }

    toggleIncludeArchived() {
        this.includeArchived = !this.includeArchived;
        this.update(this.tree);
    }

    resetDomain() {
        this.props.update("[]");
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
