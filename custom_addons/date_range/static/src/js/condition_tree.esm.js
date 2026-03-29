/* global document */
import {
    condition,
    connector,
    domainFromTree,
    formatValue,
    normalizeValue,
    treeFromDomain,
} from "@web/core/tree_editor/condition_tree";

function addChild(parent, child) {
    if (child.type === "connector" && !child.negate && child.value === parent.value) {
        parent.children.push(...child.children);
    } else {
        parent.children.push(child);
    }
}

export function removeDateRangeOperators(tree) {
    if (tree.type === "complex_condition") {
        return tree;
    }
    if (tree.type === "condition") {
        if (!tree.operator.includes("daterange")) {
            return tree;
        }
        const {negate, path, value} = tree;
        return connector(
            "&",
            [condition(path, "<=", value[0]), condition(path, ">=", value[1])],
            negate
        );
    }
    const processedChildren = tree.children.map(removeDateRangeOperators);
    if (tree.value === "|") {
        return {...tree, children: processedChildren};
    }
    const newTree = {...tree, children: []};
    // After processing a child might have become a connector "&" --> normalize
    for (let i = 0; i < processedChildren.length; i++) {
        addChild(newTree, processedChildren[i]);
    }
    return newTree;
}

function createDateRangeOperators(tree) {
    if (["condition", "complex_condition"].includes(tree.type)) {
        return tree;
    }
    const processedChildren = tree.children.map(createDateRangeOperators);
    if (tree.value === "|") {
        return {...tree, children: processedChildren};
    }
    const children = [];
    let operator = "daterange";
    if (document.getElementsByTagName("select").length) {
        operator = document
            .getElementsByTagName("select")[0]
            .selectedOptions[0].value.replace(/^"|"$/g, "");
    }
    for (let i = 0; i < processedChildren.length; i++) {
        const child1 = processedChildren[i];
        const child2 = processedChildren[i + 1];
        if (
            child1.type === "condition" &&
            child2 &&
            child2.type === "condition" &&
            formatValue(child1.path) === formatValue(child2.path) &&
            child1.operator === "<=" &&
            child2.operator === ">="
        ) {
            children.push(
                condition(
                    child1.path,
                    operator,
                    normalizeValue([child1.value, child2.value])
                )
            );
            i += 1;
        } else {
            children.push(child1);
        }
    }
    if (children.length === 1) {
        return {...children[0]};
    }
    return {...tree, children};
}

export function domainFromTreeDateRange(tree) {
    return domainFromTree(removeDateRangeOperators(tree));
}

export function treeFromDomainDateRange(domain, options = {}) {
    return createDateRangeOperators(treeFromDomain(domain, options));
}
