import { constructDomainFromTree } from "./construct_domain_from_tree";
import { eliminateVirtualOperators } from "./virtual_operators";

export function domainFromTree(tree) {
    const simplifiedTree = eliminateVirtualOperators(tree);
    return constructDomainFromTree(simplifiedTree);
}
