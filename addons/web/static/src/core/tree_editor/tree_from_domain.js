import { constructTreeFromDomain } from "./construct_tree_from_domain";
import { introduceVirtualOperators } from "./virtual_operators";

export function treeFromDomain(domain, options = {}) {
    const tree = constructTreeFromDomain(domain, options.distributeNot);
    return introduceVirtualOperators(tree, options);
}
