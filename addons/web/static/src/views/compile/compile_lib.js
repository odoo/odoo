/* @odoo-module */
import { evaluateExpr } from "@web/core/py_js/py";

/**
 * A helper to identify nodes in an arch to allow matching between
 * the parsing of an arch, and the template compilation.
 * Nodes with the same tag will be assigned an incrementing number.
 * Note that, consequently every node of the same tag should be added to produce
 * a reliable ID.
 * @return {Function} An add function to execute on each node of a given tagName
 *  Function.idFor: Produce an Id for the lastNode, or for the given node.
 */
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

/**
 * Checks if a XML node will resolve to a component when rendered by OWL.
 * @param  {Element} node Should be a node of a pre-compiled template.
 * @return {boolean}
 */
function isComponentNode(node) {
    return (
        node.tagName.charAt(0).toUpperCase() === node.tagName.charAt(0) ||
        (node.tagName === "t" && "t-component" in node.attributes)
    );
}

/**
 * Helper to add onto a Component node the information of the arch node (e.g. modifiers)
 * This is almost exclusively the support of legacy Widgets.
 * @param {Element} node A node from an arch
 * @param {Element} compiled A node of a pre-compiled template
 */
export function addLegacyNodeInfo(node, compiled) {
    const modifiers = getAllModifiers(node);
    if (modifiers) {
        const legacyNode = {
            attrs: { modifiers },
        };
        compiled.setAttribute("_legacyNode_", `"${encodeObjectForTemplate(legacyNode)}"`);
    }
}

/**
 * Encodes an object into a string usable inside a pre-compiled template
 * @param  {Object}
 * @return {string}
 */
export function encodeObjectForTemplate(obj) {
    return encodeURI(JSON.stringify(obj));
}

/**
 * Decodes a string within an attribute into an Object
 * @param  {string} str
 * @return {Object}
 */
export function decodeObjectForTemplate(str) {
    return JSON.parse(decodeURI(str));
}

/**
 * Combines the existing value of a node attribute with new given parts. The glue
 * is the string used to join the parts.
 * @param {Element} node
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
 * there is no particular expectation of what should be a boolean
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

/**
 * Gets all the Odoo's dynamic modifiers (invisible, readonly etc...) of a Node coming from an arch.
 * @param  {Element} node An arch's node
 * @return {Object} The modifiers set on the node.
 */
export function getAllModifiers(node) {
    const modifiers = node.getAttribute("modifiers");
    if (!modifiers) {
        return null;
    }
    const parsed = JSON.parse(modifiers);
    return parsed;
}

/**
 * Gets a specific modifier, either static or dynamic, on a Node.
 * A static modifier is set as an attribute and is a boolean.
 * A dynamuic modifier is set in the `modifiers` attribute and id a domain.`
 * @param  {Element} node An arch's Node.
 * @param  {string} modifierName
 * @return {boolean|Array}
 */
export function getModifier(node, modifierName) {
    /** @type {string|boolean|Array} (mod) */
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

/**
 * Specifically gets the "invisible" modifier.
 * @param  {Element} node
 * @return {boolean|Array}
 */
function getInvisible(node) {
    const invisible = getModifier(node, "invisible");
    return invisible || false;
}

/**
 * An object containing various information about the current
 * compilation from an Arch to a owl template.
 * @typedef {Object} CompilationContext
 */

/**
 * Determine if a node in an arch will always be invisible. Usually if it is the case,
 * the node will not be compiled at all
 * @param  {Element}  node   An arch's node
 * @param  {CompilationContext}
 * @return {boolean}
 */
export function isAlwaysInvisible(node, compilationContext) {
    const invisibleModifer = getInvisible(node);
    return (
        !compilationContext.enableInvisible &&
        typeof invisibleModifer === "boolean" &&
        invisibleModifer
    );
}

/**
 * Appends a child node to a parent node
 * @param  {Element} parent
 * @param  {Element|Element[]} node  The future children nodes
 */
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

/**
 * A string representing an abject that will be evaluated by a t-attr
 * eg.: `{ attr1: my_expression ? true : false, attr2: true }`
 * @typedef {string} TAttrString
 */

/**
 * A string that links an attribute to an expression
 * eg.: `my_attribute: my_expression ? true : false`
 * @typedef {string} TAttrStringPart
 */

/**
 * Helper to push in a string representing an object
 * @param  {TAttrString} originalTattr
 * @param  {TAttrStringPart} string        string to add onto the object
 * @return {TAttrString}               The new string.
 */
function appendToStringifiedObject(originalTattr, string) {
    const re = /{(.*)}/;
    const oldString = re.exec(originalTattr);

    if (oldString) {
        string = `${oldString[1]}, ${string}`;
    }
    return `{ ${string} }`;
}

/**
 * Appends a string to an attibute (t-attr)
 * @param  {Element} node
 * @param  {string} attr   The attribute's name
 * @param  {TAttrStringPart} string
 */
export function appendAttr(node, attr, string) {
    const attrKey = `t-att-${attr}`;
    const attrVal = node.getAttribute(attrKey);
    node.setAttribute(attrKey, appendToStringifiedObject(attrVal, string));
}

/**
 * Applies an arch's node invisible modifier onto a pre-compiled node
 * That is, set an t-if on the pre-compiled node, evaluating to the right expression
 * or, if enableInvisible is set in params, put the class o_invisible on the compiled node
 * @param {Object} params
 * @param  {Element} params.node     An arch's node
 * @param  {Element} params.compiled A pre-compiled node
 * @param  {CompilationContext} compilationContext
 * @param  {boolean|Array} [invisible]        A node invisible modifier
 * @return {Element|undefined}                Return the -pre-compiled
 *   Element if it is not always invisible
 */
export function applyInvisibleModifier({ node, compiled }, compilationContext, invisible) {
    if (invisible === undefined && node) {
        invisible = getInvisible(node);
    }
    if (!invisible) {
        return compiled;
    }
    if (typeof invisible === "boolean" && !compilationContext.enableInvisible) {
        return;
    }

    const notInvisibleExpr = `!model.evalDomain(record,${JSON.stringify(invisible)})`;
    if (!compilationContext.enableInvisible) {
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
