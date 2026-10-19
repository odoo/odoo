import { constructTreeFromExpression } from "./construct_tree_from_expression";
import { introduceVirtualOperators } from "./virtual_operators";

export function treeFromExpression(expression, options = {}) {
    const tree = constructTreeFromExpression(expression, options);
    return introduceVirtualOperators(tree, options);
}
