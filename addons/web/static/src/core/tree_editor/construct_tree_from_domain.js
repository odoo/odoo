import { Domain } from "@web/core/domain";
import { formatAST } from "@web/core/py_js/py";
import { addChild, connector, toValue } from "./condition_tree";

/** @typedef { import("@web/core/py_js/py_parser").AST } AST */
/** @typedef {import("@web/core/domain").DomainRepr} DomainRepr */
/** @typedef {import("./condition_tree").Tree} Tree */

/**
 * @param {AST[]} ASTs
 * @param {boolean} [distributeNot=false]
 * @param {boolean} [negate=false]
 * @returns {{ tree: Tree, remaimingASTs: AST[] }}
 */
function _constructTree(ASTs, distributeNot = false, negate = false) {
    const [firstAST, ...tailASTs] = ASTs;

    if (firstAST.type === 1 && firstAST.value === "!") {
        return _constructTree(tailASTs, distributeNot, !negate);
    }

    const tree = { type: firstAST.type === 1 ? "connector" : "condition" };
    if (tree.type === "connector") {
        tree.value = firstAST.value;
        if (distributeNot && negate) {
            tree.value = tree.value === "&" ? "|" : "&";
            tree.negate = false;
        } else {
            tree.negate = negate;
        }
        tree.children = [];
    } else {
        const [pathAST, operatorAST, valueAST] = firstAST.value;
        tree.path = toValue(pathAST);
        tree.negate = negate;
        tree.operator = toValue(operatorAST);
        tree.value = toValue(valueAST);
        if (["any", "not any"].includes(tree.operator)) {
            try {
                tree.value = constructTreeFromDomain(formatAST(valueAST), distributeNot);
            } catch {
                tree.value = Array.isArray(tree.value) ? tree.value : [tree.value];
            }
        }
    }
    let remaimingASTs = tailASTs;
    if (tree.type === "connector") {
        for (let i = 0; i < 2; i++) {
            const { tree: child, remaimingASTs: otherASTs } = _constructTree(
                remaimingASTs,
                distributeNot,
                distributeNot && negate
            );
            remaimingASTs = otherASTs;
            addChild(tree, child);
        }
    }
    return { tree, remaimingASTs };
}

/**
 * @param {DomainRepr} domain
 * @param {boolean} [distributeNot=false]
 * @returns {Tree}
 */
export function constructTreeFromDomain(domain, distributeNot = false) {
    domain = new Domain(domain);
    const domainAST = domain.ast;
    // @ts-ignore
    const initialASTs = domainAST.value;
    if (!initialASTs.length) {
        return connector("&");
    }
    const { tree } = _constructTree(initialASTs, distributeNot);
    return tree;
}
