import { constructDomainFromTree } from "./construct_domain_from_tree";
import { eliminateVirtualOperators } from "./virtual_operators";

export function domainFromTree(tree, options = {}) {
    const simplifiedTree = eliminateVirtualOperators(tree, options);
    return constructDomainFromTree(simplifiedTree);
}
