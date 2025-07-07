import { constructExpressionFromTree } from "./construct_expression_from_tree";
import { eliminateVirtualOperators } from "./virtual_operators";

export function expressionFromTree(tree, options = {}) {
    const simplifiedTree = eliminateVirtualOperators(tree);
    return constructExpressionFromTree(simplifiedTree, options);
}
