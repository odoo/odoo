/* @odoo-module */
import { evaluateExpr } from "@web/core/py_js/py";

export function nodeIdentifier() {
    const mapping = {};
    let lastNode;

    function add(node) {
        const nodeMap = mapping[node.tagName] || {
            current: null,
            id: 1,
        };
        mapping[node.tagName] = nodeMap;

        if (node !== nodeMap.current) {
            nodeMap.id++;
        }
        nodeMap.current = node;
        lastNode = node;
    }

    function idFor(node) {
        node = node || lastNode;
        const nodeMap = mapping[node.tagName];
        return `${node.tagName}_${nodeMap.id}`;
    }

    return Object.assign(add, {
        idFor(node) {
            return idFor(node);
        },
    });
}

function isComponentNode(node) {
    return (
        node.tagName.charAt(0).toUpperCase() === node.tagName.charAt(0) ||
        (node.tagName === "t" && "t-component" in node.attributes)
    );
}

export function addLegacyNodeInfo(node, compiled) {
    const modifiers = getAllModifiers(node);
    if (modifiers) {
        const legacyNode = {
            attrs: { modifiers },
        };
        compiled.setAttribute("_legacyNode_", `"${encodeObjectForTemplate(legacyNode)}"`);
    }
}

export function encodeObjectForTemplate(obj) {
    return encodeURI(JSON.stringify(obj));
}

export function decodeObjectForTemplate(str) {
    return JSON.parse(decodeURI(str));
}

/**
 * Combines the existing value of a node attribute with new given parts. The glue
 * is the string used to join the parts.
 * @param {Node} node
 * @param {string} attr
 * @param {string | string[]} parts
 * @param {string} [glue=" "]
 */
export const combineAttributes = (node, attr, parts, glue = " ") => {
    const allValues = [];
    if (node.hasAttribute(attr)) {
        allValues.push(node.getAttribute(attr));
    }
    allValues.push(...(Array.isArray(parts) ? parts : [parts]));
    node.setAttribute(attr, allValues.join(glue));
};
/**
 * there is no particular expecation of what should be a boolean
 * according to a view's arch
 * Sometimes it is 0 or one, True or False ; true or false
 * @return {boolean}
 */
function evalIrUiViewModifier(expr) {
    if (!expr) {
        return false;
    }
    return evaluateExpr(expr, {
        true: true,
        false: false,
    });
}

export function getAllModifiers(node) {
    const modifiers = node.getAttribute("modifiers");
    if (!modifiers) {
        return null;
    }
    const parsed = JSON.parse(modifiers);
    return parsed;
}

export function getModifier(node, modifierName) {
    let mod = node.getAttribute(modifierName);
    if (mod === null) {
        const modifiers = getAllModifiers(node);
        mod = modifiers && modifierName in modifiers ? modifiers[modifierName] : null;
    }

    if (!Array.isArray(mod) && !(typeof mod === "boolean")) {
        mod = !!evalIrUiViewModifier(mod);
    }
    return mod;
}

function getInvisible(node) {
    const invisible = getModifier(node, "invisible");
    return invisible || false;
}

export function isAlwaysInvisible(node, params) {
    const invisibleModifer = getInvisible(node);
    return !params.enableInvisible && typeof invisibleModifer === "boolean" && invisibleModifer;
}

export function appendTo(parent, node) {
    if (!node) {
        return;
    }
    if (Array.isArray(node) && node.length) {
        parent.append(...node);
    } else {
        parent.append(node);
    }
}

function copyAttributes(node, compiled) {
    if (node.tagName === "button") {
        return;
    }
    const classes = node.getAttribute("class");
    if (classes) {
        compiled.classList.add(...classes.split(" "));
    }

    const isComponent = isComponentNode(compiled);

    for (const attName of ["style", "placeholder"]) {
        let att = node.getAttribute(attName);
        if (att) {
            if (isComponent && attName === "placeholder") {
                att = `"${att}"`;
            }
            compiled.setAttribute(attName, att);
        }
    }
}

function appendToStringifiedObject(originalTattr, string) {
    const re = /{(.*)}/;
    const oldString = re.exec(originalTattr);

    if (oldString) {
        string = `${oldString[1]}, ${string}`;
    }
    return `{ ${string} }`;
}

export function appendAttr(node, attr, string) {
    const attrKey = `t-att-${attr}`;
    const attrVal = node.getAttribute(attrKey);
    node.setAttribute(attrKey, appendToStringifiedObject(attrVal, string));
}

export function applyInvisibleModifier({ node, compiled }, params, invisible) {
    if (invisible === undefined && node) {
        invisible = getInvisible(node);
    }
    if (!invisible) {
        return compiled;
    }
    if (typeof invisible === "boolean" && !params.enableInvisible) {
        return;
    }

    const notInvisibleExpr = `!model.evalDomain(record,${JSON.stringify(invisible)})`;
    if (!params.enableInvisible) {
        combineAttributes(compiled, "t-if", `${notInvisibleExpr}`, " and ");
    } else {
        let expr;
        if (Array.isArray(invisible)) {
            expr = `${notInvisibleExpr}`;
        } else {
            expr = invisible;
        }
        appendAttr(compiled, "class", `o_invisible_modifier: ${expr}`);
    }
    return compiled;
}
