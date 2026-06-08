import { Expression, isTree } from "./condition_tree";
import { constructTreeFromDomain } from "./construct_tree_from_domain";

function treeContainsExpressions(tree) {
    if (tree.type === "condition") {
        const { path, operator, value } = tree;
        if (isTree(value) && treeContainsExpressions(value)) {
            return true;
        }
        return [path, operator, value].some(
            (v) =>
                v instanceof Expression ||
                (Array.isArray(v) && v.some((w) => w instanceof Expression))
        );
    }
    for (const child of tree.children) {
        if (treeContainsExpressions(child)) {
            return true;
        }
    }
    return false;
}

export function domainContainsExpressions(domain) {
    let tree;
    try {
        tree = constructTreeFromDomain(domain);
    } catch {
        return null;
    }
    // detect expressions in the domain tree, which we know is well-formed
    return treeContainsExpressions(tree);
}
