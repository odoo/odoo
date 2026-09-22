import { registry } from "@web/core/registry";
import { Plugin } from "@mail/convert_inline/plugin";
import { isListElement, isListItemElement } from "@html_editor/utils/dom_info";
import { childNodes } from "@html_editor/utils/dom_traversal";
import { FakeListContainer, FakeListItem } from "@mail/convert_inline/main/list_models";

export class ListStrategyPlugin extends Plugin {
    static id = "listStrategy";
    static dependencies = ["contextStyle", "measurementSnapshot"];
    resources = {
        element_layout_analysis_processors: this.analyzeFakeListLayout.bind(this),
        cell_ref_name_processors: [this.getCellRefName.bind(this)],
        style_rules_processors: this.provideStyleRules.bind(this),
    };

    /**
     * TODO EGGMAIL: simplified algorithm, to update if insufficient:
     * detect a list where `li` elements don't have display: list-item
     * in such a case, render a table instead.
     */
    analyzeFakeListLayout(defaultEmailNodeArguments, { referenceNode, parentEmailNode }) {
        let { layout, analysis } = defaultEmailNodeArguments;
        let detectionResult;
        if ((detectionResult = this.detectFakeListContainer(referenceNode))) {
            analysis.buildDirectives.canMerge = false;
            analysis.facts.isFakeListContainer = true;
            layout = this.buildFakeListContainer(layout);
        } else if (
            parentEmailNode?.analysis.facts.isFakeListContainer &&
            (detectionResult = this.detectFakeListItem(referenceNode))
        ) {
            analysis.buildDirectives.canMerge = true;
            analysis.facts.attemptCellMerge = true;
            layout = this.buildFakeListItem(layout, referenceNode);
        }
        if (detectionResult) {
            analysis.buildDirectives.canParentMerge = false;
            return { layout, analysis };
        }
        return defaultEmailNodeArguments;
    }

    provideStyleRules(rules) {
        // block existing margin-top
        rules.block("margin-top", {
            when: ({ referenceNode }) => isListElement(referenceNode),
        });
        rules.require("margin-top", {
            when: ({ referenceNode }) => isListElement(referenceNode),
            how: () => ({ propertyValue: "0", propertyPriority: "important" }),
        });
    }

    detectFakeListContainer(referenceNode) {
        if (!isListElement(referenceNode)) {
            return;
        }
        const children = childNodes(referenceNode);
        return children.some((item) => this.detectFakeListItem(item));
    }

    detectFakeListItem(referenceNode) {
        if (!isListItemElement(referenceNode)) {
            return;
        }
        return this.getStylePropertyValue(referenceNode, "display") !== "list-item";
    }

    buildFakeListContainer(layout) {
        return new FakeListContainer({
            refs: { root: layout.getRef() },
        });
    }

    buildFakeListItem(layout, referenceNode) {
        return new FakeListItem({
            refs: {
                cell: { style: this.getTableContextStyleInfo(referenceNode) },
                div: layout.getRef(),
            },
        });
    }

    getCellRefName(refName, emailNode) {
        if (emailNode.layout instanceof FakeListItem) {
            return "div";
        }
        return refName;
    }
}

registry
    .category("mail-html-conversion-main-plugins")
    .add(ListStrategyPlugin.id, ListStrategyPlugin);
