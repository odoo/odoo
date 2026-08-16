import { Component, asyncComputed, onWillStart, signal, t, useProps } from "@odoo/owl";
import { CheckBox } from "@web/core/checkbox/checkbox";
import { Domain } from "@web/core/domain";
import { getDomainDisplayedOperators } from "@web/core/domain_selector/domain_selector_operator_editor";
import { _t } from "@web/core/l10n/translation";
import { ModelFieldSelector } from "@web/core/model_field_selector/model_field_selector";
import {
    areEqualTrees,
    condition,
    connector,
    formatValue,
} from "@web/core/tree_editor/condition_tree";
import { domainFromTree } from "@web/core/tree_editor/domain_from_tree";
import { TreeEditor } from "@web/core/tree_editor/tree_editor";
import { getOperatorEditorInfo } from "@web/core/tree_editor/tree_editor_operator_editor";
import { useService } from "@web/core/utils/hooks";
import { getDefaultCondition } from "./utils";

const ARCHIVED_CONDITION = condition("active", "in", [true, false]);
const ARCHIVED_DOMAIN = `[("active", "in", [True, False])]`;

export const domainSelectorProps = {
    domain: t.string(),
    resModel: t.string(),
    className: t.string().optional(),
    defaultConnector: t.selection(["&", "|"]).optional(),
    isDebugMode: t.boolean().optional(false),
    readonly: t.boolean().optional(true),
    update: t.function().optional(() => () => {}),
    debugUpdate: t.function().optional(),
};

export class DomainSelector extends Component {
    static template = "web.DomainSelector";
    static components = { TreeEditor, CheckBox };
    props = useProps(domainSelectorProps);

    includeArchived = signal(false);

    setup() {
        this.fieldService = useService("field");
        this.treeProcessor = useService("tree_processor");

        this.info = asyncComputed(() => this.loadInfo(), {
            initial: { tree: null, showArchivedCheckbox: false },
        });
        onWillStart(async () => {
            await this.info.currentPromise();
        });
    }

    async loadInfo() {
        // Reactive reads have to happen on the synchronous path: anything read
        // after the first `await` is not tracked as a dependency.
        const { domain: rawDomain, isDebugMode, resModel } = this.props;
        let domain;
        try {
            domain = new Domain(rawDomain);
        } catch {
            this.includeArchived.set(false);
            return { tree: null, showArchivedCheckbox: false };
        }

        const [tree, { fieldDef: activeFieldDef }] = await Promise.all([
            this.treeProcessor.treeFromDomain(resModel, domain, !isDebugMode),
            this.fieldService.loadFieldInfo(resModel, "active"),
        ]);

        const info = {
            tree,
            showArchivedCheckbox: this.getShowArchivedCheckBox(Boolean(activeFieldDef), this.props),
        };

        let includeArchived = false;
        if (info.showArchivedCheckbox) {
            if (info.tree.type === "connector" && info.tree.value === "&") {
                info.tree.children = info.tree.children.filter((child) => {
                    if (areEqualTrees(child, ARCHIVED_CONDITION)) {
                        includeArchived = true;
                        return false;
                    }
                    return true;
                });
                if (info.tree.children.length === 1) {
                    info.tree = info.tree.children[0];
                }
            } else if (areEqualTrees(info.tree, ARCHIVED_CONDITION)) {
                includeArchived = true;
                info.tree = connector("&");
            }
        }
        this.includeArchived.set(includeArchived);
        return info;
    }

    get tree() {
        return this.info().tree;
    }

    get showArchivedCheckbox() {
        return this.info().showArchivedCheckbox;
    }

    getShowArchivedCheckBox(hasActiveField, props) {
        return hasActiveField;
    }

    getDefaultCondition(fieldDefs) {
        return getDefaultCondition(fieldDefs);
    }

    getDefaultOperator(fieldDef) {
        return getDomainDisplayedOperators(fieldDef)[0];
    }

    getOperatorEditorInfo(fieldDef) {
        const operators = getDomainDisplayedOperators(fieldDef);
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
        this.includeArchived.set(!this.includeArchived());
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
        const archiveDomain = this.includeArchived() ? ARCHIVED_DOMAIN : `[]`;
        const domain = tree
            ? Domain.and([domainFromTree(tree), archiveDomain]).toString()
            : archiveDomain;
        this.props.update(domain);
    }
}
