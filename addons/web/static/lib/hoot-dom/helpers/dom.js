/** @odoo-module */

import { getTag, isFirefox, isInstanceOf, isIterable, parseRegExp } from "../hoot_dom_utils";
import { waitUntil } from "./time";

/**
 * @typedef {number | [number, number] | {
 *  w?: number;
 *  h?: number;
 *  width?: number;
 *  height?: number;
 * }} Dimensions
 *
 * @typedef {{
 *  root?: Target;
 *  tabbable?: boolean;
 * }} FocusableOptions
 *
 * @typedef {{
 *  keepInlineTextNodes?: boolean;
 *  tabSize?: number;
 *  type?: "html" | "xml";
 * }} FormatXmlOptions
 *
 * @typedef {{
 *  inline: boolean;
 *  level: number;
 *  value: MarkupLayerValue;
 * }} MarkupLayer
 *
 * @typedef {{
 *  close?: string;
 *  open?: string;
 *  textContent?: string;
 * }} MarkupLayerValue
 *
 * @typedef {(node: Node, index: number, nodes: Node[]) => boolean | Node} NodeFilter
 *
 * @typedef {(node: Node, selector: string) => Node[]} NodeGetter
 *
 * @typedef {string | string[] | number | boolean | File[]} NodeValue
 *
 * @typedef {number | [number, number] | {
 *  x?: number;
 *  y?: number;
 *  left?: number;
 *  top?: number,
 *  clientX?: number;
 *  clientY?: number;
 *  pageX?: number;
 *  pageY?: number;
 *  screenX?: number;
 *  screenY?: number;
 * }} Position
 *
 * @typedef {(content: string) => QueryFilter} PseudoClassPredicateBuilder
 *
 * @typedef {string | number | NodeFilter} QueryFilter
 *
 * @typedef {{
 *  contains?: string;
 *  displayed?: boolean;
 *  empty?: boolean;
 *  eq?: number;
 *  exact?: number;
 *  first?: boolean;
 *  focusable?: boolean;
 *  has?: boolean;
 *  hidden?: boolean;
 *  iframe?: boolean;
 *  interactive?: boolean;
 *  last?: boolean;
 *  not?: boolean;
 *  only?: boolean;
 *  root?: HTMLElement;
 *  scrollable?: ScrollAxis;
 *  selected?: boolean;
 *  shadow?: boolean;
 *  value?: boolean;
 *  viewPort?: boolean;
 *  visible?: boolean;
 * }} QueryOptions
 *
 * @typedef {{
 *  trimPadding?: boolean;
 * }} QueryRectOptions
 *
 * @typedef {{
 *  inline?: boolean;
 *  raw?: boolean;
 * }} QueryTextOptions
 *
 * @typedef {"both" | "x" | "y"} ScrollAxis
 *
 * @typedef {import("./time").WaitOptions} WaitOptions
 */

/**
 * @template T
 * @typedef {T | Iterable<T>} MaybeIterable
 */

/**
 * @template [T=Node]
 * @typedef {MaybeIterable<T> | string | null | undefined | false} Target
 */

//-----------------------------------------------------------------------------
// Global
//-----------------------------------------------------------------------------

const {
    document,
    DOMParser,
    Error,
    innerWidth,
    innerHeight,
    Map,
    MutationObserver,
    Number: { isInteger: $isInteger, isNaN: $isNaN, parseInt: $parseInt, parseFloat: $parseFloat },
    Object: { entries: $entries, keys: $keys, values: $values },
    RegExp,
    Set,
    String: { raw: $raw },
    window,
} = globalThis;

//-----------------------------------------------------------------------------
// Internal
//-----------------------------------------------------------------------------

/**
 * @param {Iterable<QueryFilter>} filters
 * @param {Node[]} nodes
 */
function applyFilters(filters, nodes) {
    for (const filter of filters) {
        const filteredGroupNodes = [];
        for (let i = 0; i < nodes.length; i++) {
            const result = matchFilter(filter, nodes, i);
            if (result === true) {
                filteredGroupNodes.push(nodes[i]);
            } else if (result) {
                filteredGroupNodes.push(result);
            }
        }
        nodes = filteredGroupNodes;
        if (globalFilterDescriptors.has(filter)) {
            globalFilterDescriptors.get(filter).push(nodes.length);
        } else if (selectorFilterDescriptors.has(filter)) {
            selectorFilterDescriptors.get(filter).push(nodes.length);
        }
    }
    return nodes;
}

function compilePseudoClassRegex() {
    const customKeys = [...customPseudoClasses.keys()].filter((k) => k !== "has" && k !== "not");
    return new RegExp(`:(${customKeys.join("|")})`);
}

/**
 * @param {Element[]} elements
 * @param {string} selector
 */
function elementsMatch(elements, selector) {
    if (!elements.length) {
        return false;
    }
    return parseSelector(selector).some((selectorParts) => {
        const [baseSelector, ...filters] = selectorParts.at(-1);
        for (let i = 0; i < elements.length; i++) {
            if (baseSelector && !elements[i].matches(baseSelector)) {
                return false;
            }
            if (!filters.every((filter) => matchFilter(filter, elements, i))) {
                return false;
            }
        }
        return true;
    });
}

/**
 * @param {QueryOptions} options
 */
function ensureCount(options) {
    options = { ...options };
    if (!("eq" in options || "first" in options || "last" in options)) {
        options.first = true;
    }
    return options;
}

/**
 * @param {Node} node
 * @returns {Element | null}
 */
function ensureElement(node) {
    if (node) {
        if (isDocument(node)) {
            return node.documentElement;
        }
        if (isWindow(node)) {
            return node.document.documentElement;
        }
        if (isElement(node)) {
            return node;
        }
    }
    return null;
}

/**
 * @param {Iterable<Node>} nodes
 * @param {number} level
 * @param {boolean} [keepInlineTextNodes]
 */
function extractLayers(nodes, level, keepInlineTextNodes) {
    /** @type {MarkupLayer[]} */
    const layers = [];
    for (const node of nodes) {
        if (node.nodeType === Node.COMMENT_NODE) {
            continue;
        }
        if (node.nodeType === Node.TEXT_NODE) {
            const textContent = node.nodeValue.replaceAll(/\n/g, "");
            const trimmedTextContent = textContent.trim();
            if (trimmedTextContent) {
                const inline = textContent === trimmedTextContent;
                layers.push({ inline, level, value: { textContent: trimmedTextContent } });
            }
            continue;
        }
        const [open, close] = node.outerHTML.replace(`>${node.innerHTML}<`, ">\n<").split("\n");
        const layer = { inline: false, level, value: { open, close } };
        layers.push(layer);
        const childLayers = extractLayers(node.childNodes, level + 1, false);
        if (keepInlineTextNodes && childLayers.length === 1 && childLayers[0].inline) {
            layer.value.textContent = childLayers[0].value.textContent;
        } else {
            layers.push(...childLayers);
        }
    }
    return layers;
}

/**
 * @param {Iterable<Node>} nodesToFilter
 */
function filterUniqueNodes(nodesToFilter) {
    /** @type {Node[]} */
    const nodes = [];
    for (const node of nodesToFilter) {
        if (isQueryableNode(node) && !nodes.includes(node)) {
            nodes.push(node);
        }
    }
    return nodes;
}

/**
 * @param {MarkupLayer[]} layers
 * @param {number} tabSize
 */
function generateStringFromLayers(layers, tabSize) {
    const result = [];
    let layerIndex = 0;
    while (layers.length > 0) {
        const layer = layers[layerIndex];
        const { level, value } = layer;
        const pad = " ".repeat(tabSize * level);
        let nextLayerIndex = layerIndex + 1;
        if (value.open) {
            if (value.textContent) {
                // node with inline textContent (no wrapping white-spaces)
                result.push(`${pad}${value.open}${value.textContent}${value.close}`);
                layers.splice(layerIndex, 1);
                nextLayerIndex--;
            } else {
                result.push(`${pad}${value.open}`);
                delete value.open;
            }
        } else {
            if (value.close) {
                result.push(`${pad}${value.close}`);
            } else if (value.textContent) {
                result.push(`${pad}${value.textContent}`);
            }
            layers.splice(layerIndex, 1);
            nextLayerIndex--;
        }
        if (nextLayerIndex >= layers.length) {
            layerIndex = nextLayerIndex - 1;
            continue;
        }
        const nextLayer = layers[nextLayerIndex];
        if (nextLayerIndex === 0 || nextLayer.level > layers[nextLayerIndex - 1].level) {
            layerIndex = nextLayerIndex;
        } else {
            layerIndex = nextLayerIndex - 1;
        }
    }
    return result.join("\n");
}

/**
 * @param {[string, string, number][]} modifierInfo
 */
function getFiltersDescription(modifierInfo) {
    const description = [];
    for (const [modifier, content, count = 0] of modifierInfo) {
        const makeLabel = MODIFIER_SUFFIX_LABELS[modifier];
        const elements = plural("element", count);
        if (typeof makeLabel === "function") {
            description.push(`${count} ${elements} ${makeLabel(content)}`);
        } else {
            description.push(`${count} ${modifier} ${elements}`);
        }
        if (!count) {
            // Stop at first null count to avoid situations like:
            // "found 0 elements, including 0 visible elements, including 0 ..."
            break;
        }
    }
    return description;
}

/**
 * @param {Node} node
 * @returns {NodeValue}
 */
function getNodeContent(node) {
    switch (getTag(node)) {
        case "input":
        case "option":
        case "textarea":
            return getNodeValue(node);
        case "select":
            return [...node.selectedOptions].map(getNodeValue).join(",");
    }
    return getNodeText(node);
}

/** @type {NodeFilter} */
function getNodeIframe(node) {
    // Note: should only apply on `iframe` elements
    /** @see parseSelector */
    const doc = node.contentDocument;
    return doc && doc.readyState !== "loading" ? doc : false;
}

/** @type {NodeFilter} */
function getNodeShadowRoot(node) {
    return node.shadowRoot;
}

/**
 * @param {string} string
 */
function getStringContent(string) {
    return string.match(R_QUOTE_CONTENT)?.[2] || string;
}

function getWaitForMessage() {
    const message = `expected at least 1 element after %timeout%ms and ${lastQueryMessage}`;
    lastQueryMessage = "";
    return message;
}

function getWaitForNoneMessage() {
    const message = `expected 0 elements after %timeout%ms and ${lastQueryMessage}`;
    lastQueryMessage = "";
    return message;
}

/**
 * @param {string} [char]
 */
function isChar(char) {
    return !!char && R_CHAR.test(char);
}

/**
 * @template T
 * @param {T} object
 * @returns {T extends Document ? true : false}
 */
function isDocument(object) {
    return object?.nodeType === Node.DOCUMENT_NODE;
}

/**
 * @template T
 * @param {T} object
 * @returns {T extends Element ? true: false}
 */
function isElement(object) {
    return object?.nodeType === Node.ELEMENT_NODE;
}

/**
 * @param {string} selector
 * @param {Node} node
 */
function isNodeHaving(selector, node) {
    return !!_queryAll(selector, { root: node }).length;
}

/** @type {NodeFilter} */
function isNodeHidden(node) {
    return !isNodeVisible(node);
}

/** @type {NodeFilter} */
function isNodeInteractive(node) {
    return (
        getStyle(node).pointerEvents !== "none" &&
        !node.closest?.("[inert]") &&
        !getParentFrame(node)?.inert
    );
}

/**
 * @param {string} selector
 * @param {Node} node
 */
function isNodeNotMatching(selector, node) {
    return !matches(node, selector);
}

/** @type {NodeFilter} */
function isNodeSelected(node) {
    return !!node.selected;
}

/** @type {NodeFilter} */
function isOnlyNode(_node, _i, nodes) {
    return nodes.length === 1;
}

/**
 * @param {Node} node
 */
function isQueryableNode(node) {
    return QUERYABLE_NODE_TYPES.includes(node.nodeType);
}

/**
 * @param {Element} [el]
 */
function isRootElement(el) {
    return el && R_ROOT_ELEMENT.test(el.nodeName || "");
}

/**
 * @param {Element} el
 */
function isShadowRoot(el) {
    return el.nodeType === Node.DOCUMENT_FRAGMENT_NODE && !!el.host;
}

/**
 * @template T
 * @param {T} object
 * @returns {T extends Window ? true : false}
 */
function isWindow(object) {
    return object?.window === object && object.constructor.name === "Window";
}

/**
 * @param {string} [char]
 */
function isWhiteSpace(char) {
    return !!char && R_HORIZONTAL_WHITESPACE.test(char);
}

/**
 * @param {string} pseudoClass
 * @param {(node: Node) => NodeValue} getContent
 */
function makePatternBasedPseudoClass(pseudoClass, getContent) {
    return (content) => {
        let regex;
        try {
            regex = parseRegExp(content);
        } catch (err) {
            throw selectorError(pseudoClass, err.message);
        }
        if (isInstanceOf(regex, RegExp)) {
            return function containsRegExp(node) {
                return regex.test(String(getContent(node)));
            };
        } else {
            const lowerContent = content.toLowerCase();
            return function containsString(node) {
                return getStringContent(String(getContent(node)))
                    .toLowerCase()
                    .includes(lowerContent);
            };
        }
    };
}

/**
 *
 * @param {QueryFilter} filter
 * @param {Node[]} nodes
 * @param {number} index
 */
function matchFilter(filter, nodes, index) {
    if (typeof filter === "number") {
        if (filter < 0) {
            return filter + nodes.length === index;
        } else {
            return filter === index;
        }
    }
    const node = nodes[index];
    if (typeof filter === "function") {
        return filter(node, index, nodes);
    } else {
        return !!node.matches?.(String(filter));
    }
}

/**
 * flatMap implementation supporting NodeList iterables.
 *
 * @param {Iterable<Node>} nodes
 * @param {(node: Node) => Node | Iterable<Node> | null | undefined} flatMapFn
 */
function nodeFlatMap(nodes, flatMapFn) {
    /** @type {Node[]} */
    const result = [];
    for (const node of nodes) {
        const nodeList = flatMapFn(node);
        if (isNode(nodeList)) {
            result.push(nodeList);
        } else if (isIterable(nodeList)) {
            result.push(...nodeList);
        }
    }
    return result;
}

/**
 * @template T
 * @param {T} value
 * @param {(keyof T)[]} propsA
 * @param {(keyof T)[]} propsB
 * @returns {[number, number]}
 */
function parseNumberTuple(value, propsA, propsB) {
    let result = [];
    if (value && typeof value === "object") {
        if (isIterable(value)) {
            [result[0], result[1]] = [...value];
        } else {
            for (const prop of propsA) {
                result[0] ??= value[prop];
            }
            for (const prop of propsB) {
                result[1] ??= value[prop];
            }
        }
    } else {
        result = [value, value];
    }
    return result.map($parseFloat);
}

/**
 * @template {any[]} T
 * @param {T} args
 * @returns {string | T}
 */
function parseRawArgs(args) {
    return args[0]?.raw ? [$raw(...args)] : args;
}

/**
 * Parses a given selector string into a list of selector groups.
 *
 * - the return value is a list of selector `group` objects (representing comma-separated
 *  selectors);
 * - a `group` is composed of one or more `part` objects (representing space-separated
 *  selector parts inside of a group);
 * - a `part` is composed of a base selector (string) and zero or more 'filters' (predicates).
 *
 * @param {string} selector
 */
function parseSelector(selector) {
    /**
     * @param {string} selector
     */
    function addToSelector(selector) {
        registerChar = false;
        const index = currentPart.length - 1;
        if (typeof currentPart[index] === "string") {
            currentPart[index] += selector;
        } else {
            currentPart.push(selector);
        }
    }

    /** @type {(string | ReturnType<PseudoClassPredicateBuilder>)[]} */
    const firstPart = [""];
    const firstGroup = [firstPart];
    const groups = [firstGroup];
    const parens = [0, 0];

    let currentGroup = groups.at(-1);
    let currentPart = currentGroup.at(-1);
    let currentPseudo = null;
    let currentQuote = null;
    let registerChar = true;

    for (let i = 0; i < selector.length; i++) {
        const char = selector[i];
        registerChar = true;
        switch (char) {
            // Group separator (comma)
            case ",": {
                if (!currentQuote && !currentPseudo) {
                    groups.push([[""]]);
                    currentGroup = groups.at(-1);
                    currentPart = currentGroup.at(-1);
                    registerChar = false;
                }
                break;
            }
            // Part separator (white space)
            case " ":
            case "\t":
            case "\n":
            case "\r":
            case "\f":
            case "\v": {
                if (!currentQuote && !currentPseudo) {
                    if (currentPart[0] || currentPart.length > 1) {
                        // Only push new part if the current one is not empty
                        // (has at least 1 character OR 1 pseudo-class filter)
                        currentGroup.push([""]);
                        currentPart = currentGroup.at(-1);
                    }
                    registerChar = false;
                }
                break;
            }
            // Quote delimiters
            case `'`:
            case `"`: {
                if (char === currentQuote) {
                    currentQuote = null;
                } else if (!currentQuote) {
                    currentQuote = char;
                }
                break;
            }
            // Combinators
            case ">":
            case "+":
            case "~": {
                if (!currentQuote && !currentPseudo) {
                    while (isWhiteSpace(selector[i + 1])) {
                        i++;
                    }
                    addToSelector(char);
                }
                break;
            }
            // Pseudo classes
            case ":": {
                if (!currentQuote && !currentPseudo) {
                    let pseudo = "";
                    while (isChar(selector[i + 1])) {
                        pseudo += selector[++i];
                    }
                    if (customPseudoClasses.has(pseudo)) {
                        if (selector[i + 1] === "(") {
                            parens[0]++;
                            i++;
                            registerChar = false;
                        }
                        currentPseudo = [pseudo, ""];
                    } else {
                        addToSelector(char + pseudo);
                    }
                }
                break;
            }
            // Parentheses
            case "(": {
                if (!currentQuote) {
                    parens[0]++;
                }
                break;
            }
            case ")": {
                if (!currentQuote) {
                    parens[1]++;
                }
                break;
            }
        }

        if (currentPseudo) {
            if (parens[0] === parens[1]) {
                const [pseudo, content] = currentPseudo;
                const makeFilter = customPseudoClasses.get(pseudo);
                if (pseudo === "iframe" && !currentPart[0].startsWith("iframe")) {
                    // Special case: to optimise the ":iframe" pseudo class, we
                    // always select actual `iframe` elements.
                    // Note that this may create "impossible" tag names (like "iframediv")
                    // but this pseudo won't work on non-iframe elements anyway.
                    currentPart[0] = `iframe${currentPart[0]}`;
                }
                const filter = makeFilter(getStringContent(content));
                selectorFilterDescriptors.set(filter, [pseudo, content]);
                currentPart.push(filter);
                currentPseudo = null;
            } else if (registerChar) {
                currentPseudo[1] += selector[i];
            }
        } else if (registerChar) {
            addToSelector(selector[i]);
        }
    }

    return groups;
}

/**
 * @param {string} xmlString
 * @param {"html" | "xml"} type
 */
function parseXml(xmlString, type) {
    const wrapperTag = type === "html" ? "body" : "templates";
    const doc = parser.parseFromString(
        `<${wrapperTag}>${xmlString}</${wrapperTag}>`,
        `text/${type}`
    );
    if (doc.getElementsByTagName("parsererror").length) {
        const trimmed = xmlString.length > 80 ? xmlString.slice(0, 80) + "…" : xmlString;
        throw new HootDomError(
            `error while parsing ${trimmed}: ${getNodeText(
                doc.getElementsByTagName("parsererror")[0]
            )}`
        );
    }
    return doc.getElementsByTagName(wrapperTag)[0].childNodes;
}

/**
 * Converts a CSS pixel value to a number, removing the 'px' part.
 *
 * @param {string} val
 */
function pixelValueToNumber(val) {
    return $parseFloat(val.endsWith("px") ? val.slice(0, -2) : val);
}

/**
 * @param {string} word
 * @param {number} count
 */
function plural(word, count) {
    return count === 1 ? word : `${word}s`;
}

/**
 * @param {Node[]} nodes (assumed not empty)
 * @param {string} selector
 */
function queryWithCustomSelector(nodes, selector) {
    const selectorGroups = parseSelector(selector);
    const foundNodes = [];
    for (const selectorParts of selectorGroups) {
        let groupNodes = nodes;
        for (const selectorPart of selectorParts) {
            let baseSelector = selectorPart[0];
            let nodeGetter;
            switch (baseSelector[0]) {
                case "+": {
                    nodeGetter = NEXT_SIBLING;
                    break;
                }
                case ">": {
                    nodeGetter = DIRECT_CHILDREN;
                    break;
                }
                case "~": {
                    nodeGetter = NEXT_SIBLINGS;
                    break;
                }
            }

            // Slices modifier (if any)
            if (nodeGetter) {
                baseSelector = baseSelector.slice(1);
            }
            nodeGetter ||= DESCENDANTS;

            // Retrieve nodes from current group nodes
            const currentGroupNodes = nodeFlatMap(groupNodes, (node) =>
                nodeGetter(node, baseSelector)
            );

            // Filter/replace nodes based on custom pseudo-classes
            groupNodes = applyFilters(selectorPart.slice(1), currentGroupNodes);
        }

        foundNodes.push(...groupNodes);
    }

    return filterUniqueNodes(foundNodes);
}

/**
 * Creates a query message if needed, with all the information available used to
 * gather the given nodes (base selector and count of nodes matching it, then each
 * modifier applied as a filter with each associated count).
 *
 * Returns the resulting message only if the final count of nodes doesn't match
 * the given expected count.
 *
 * @param {Node[]} filteredNodes
 * @param {number} [expectedCount]
 */
function registerQueryMessage(filteredNodes, expectedCount) {
    lastQueryMessage = "";
    const filteredCount = filteredNodes.length;
    const invalidCount = $isInteger(expectedCount) && filteredCount !== expectedCount;
    if (shouldRegisterQueryMessage || invalidCount) {
        const globalModifierInfo = [...globalFilterDescriptors.values()];

        // First message part: final count
        lastQueryMessage += `found ${filteredCount} ${plural("element", filteredCount)}`;
        if (invalidCount) {
            lastQueryMessage += ` instead of ${expectedCount}`;
        }

        // Next message part: initial element count (with selector if string)
        const rootModifierInfo = globalModifierInfo.shift();
        const [, rootContent, initialCount = 0] = rootModifierInfo;
        if (typeof rootContent === "string") {
            lastQueryMessage += `: ${initialCount} matching ${JSON.stringify(rootContent)}`;
            if (selectorFilterDescriptors.size) {
                // Selector filters will only be available with a custom selector
                const selectorModifierInfo = [...selectorFilterDescriptors.values()];
                lastQueryMessage += ` (${getFiltersDescription(selectorModifierInfo).join(" > ")})`;
            }
        } else if (filteredCount !== initialCount) {
            // Do not report count if same as announced initially
            lastQueryMessage += `: ${initialCount} ${plural("element", initialCount)}`;
        }
        if (initialCount) {
            // Next message parts: each count associated with each modifier
            lastQueryMessage += getFiltersDescription(globalModifierInfo)
                .map((part) => `, including ${part}`)
                .join("");
        }
    } else {
        lastQueryMessage = "";
    }
    if (queryAllLevel <= 1) {
        globalFilterDescriptors.clear();
        selectorFilterDescriptors.clear();
    }
    return invalidCount ? lastQueryMessage : "";
}

/**
 * @param {string} pseudoClass
 * @param {string} message
 */
function selectorError(pseudoClass, message) {
    return new HootDomError(`invalid selector \`:${pseudoClass}\`: ${message}`);
}

/**
 * Wrapper around '_queryAll' calls to ensure global variables are properly cleaned
 * up on any thrown error.
 *
 * @param {Target} target
 * @param {QueryOptions} options
 */
function _guardedQueryAll(target, options) {
    try {
        return _queryAll(target, options);
    } catch (error) {
        queryAllLevel = 0;
        shouldRegisterQueryMessage = false;
        globalFilterDescriptors.clear();
        selectorFilterDescriptors.clear();
        throw error;
    }
}

/**
 * @param {Target} target
 * @param {QueryOptions} options
 */
function _queryAll(target, options) {
    queryAllLevel++;

    const { exact, root, ...modifiers } = options || {};

    /** @type {Node[]} */
    let nodes = [];
    let selector;

    if (typeof target === "string") {
        if (target) {
            nodes = root ? _queryAll(root) : [getDefaultRoot()];
        }
        selector = target.trim();
        // HTMLSelectElement is iterable ¯\_(ツ)_/¯
    } else if (isIterable(target) && !isNode(target)) {
        nodes = filterUniqueNodes(target);
    } else if (target) {
        nodes = filterUniqueNodes([target]);
    }

    globalFilterDescriptors.set("root", ["", target]);
    if (selector && nodes.length) {
        if (rCustomPseudoClass.test(selector)) {
            nodes = queryWithCustomSelector(nodes, selector);
        } else {
            nodes = filterUniqueNodes(nodeFlatMap(nodes, (node) => DESCENDANTS(node, selector)));
        }
    }
    globalFilterDescriptors.get("root").push(nodes.length);

    if (modifiers.visible && modifiers.displayed) {
        throw new HootDomError(
            `cannot use more than one visibility modifier ('visible' implies 'displayed')`
        );
    }

    // Apply option modifiers on matching nodes
    const modifierFilters = [];
    for (const [modifier, content] of $entries(modifiers)) {
        if (content === false || !customPseudoClasses.has(modifier)) {
            continue;
        }
        const makeFilter = customPseudoClasses.get(modifier);
        const filter = makeFilter(content);
        modifierFilters.push(filter);
        globalFilterDescriptors.set(filter, [modifier, content]);
    }
    const filteredNodes = applyFilters(modifierFilters, nodes);

    // Register query message (if needed), and/or throw an error accordingly
    const message = registerQueryMessage(filteredNodes, exact);
    if (message) {
        throw new HootDomError(message);
    }

    queryAllLevel--;

    return filteredNodes;
}

/**
 * @param {Target} target
 * @param {QueryOptions} options
 */
function _queryOne(target, options) {
    return _guardedQueryAll(target, { ...options, exact: 1 })[0];
}

/**
 * @param {Target} target
 * @param {QueryOptions} options
 * @param {boolean} isLast
 */
function _waitForFirst(target, options, isLast) {
    shouldRegisterQueryMessage = isLast;
    const result = _guardedQueryAll(target, options)[0];
    shouldRegisterQueryMessage = false;
    return result;
}

/**
 * @param {Target} target
 * @param {QueryOptions} options
 * @param {boolean} isLast
 */
function _waitForNone(target, options, isLast) {
    shouldRegisterQueryMessage = isLast;
    const result = _guardedQueryAll(target, options).length === 0;
    shouldRegisterQueryMessage = false;
    return result;
}

class HootDomError extends Error {
    name = "HootDomError";
}

// Regexes
const R_CHAR = /[\w-]/;
/** \s without \n and \v */
const R_HORIZONTAL_WHITESPACE =
    /[\r\t\f \u00a0\u1680\u2000-\u200a\u2028\u2029\u202f\u205f\u3000\ufeff]+/g;
const R_LINEBREAK = /\s*\n+\s*/g;
const R_QUOTE_CONTENT = /^\s*(['"])?([^]*?)\1\s*$/;
const R_ROOT_ELEMENT = /^(HTML|HEAD|BODY)$/;
const R_SCROLLABLE_OVERFLOW = /\bauto\b|\bscroll\b/;

const MODIFIER_SUFFIX_LABELS = {
    contains: (content) => `with text "${content}"`,
    eq: (content) => `at index ${content}`,
    has: (content) => `containing selector "${content}"`,
    not: (content) => `not matching "${content}"`,
    value: (content) => `with value "${content}"`,
    viewPort: () => "in viewport",
};

const QUERYABLE_NODE_TYPES = [Node.ELEMENT_NODE, Node.DOCUMENT_NODE, Node.DOCUMENT_FRAGMENT_NODE];

const parser = new DOMParser();

// Node getters

/** @type {NodeGetter} */
function DIRECT_CHILDREN(node, selector) {
    const children = [];
    for (const childNode of node.childNodes) {
        if (childNode.matches?.(selector)) {
            children.push(childNode);
        }
    }
    return children;
}

/** @type {NodeGetter} */
function DESCENDANTS(node, selector) {
    return node.querySelectorAll?.(selector || "*");
}

/** @type {NodeGetter} */
function NEXT_SIBLING(node, selector) {
    const sibling = node.nextElementSibling;
    return sibling?.matches?.(selector) && sibling;
}

/** @type {NodeGetter} */
function NEXT_SIBLINGS(node, selector) {
    const siblings = [];
    while ((node = node.nextElementSibling)) {
        if (node.matches?.(selector)) {
            siblings.push(node);
        }
    }
    return siblings;
}

/** @type {Map<QueryFilter, [string, string | null, number]>} */
const globalFilterDescriptors = new Map();
/** @type {Map<QueryFilter, [string, string | null, number]>} */
const selectorFilterDescriptors = new Map();
/** @type {Map<HTMLElement, { callbacks: Set<MutationCallback>, observer: MutationObserver }>} */
const observers = new Map();
const currentDimensions = {
    width: innerWidth,
    height: innerHeight,
};
let getDefaultRoot = () => document;
let lastQueryMessage = "";
let shouldRegisterQueryMessage = false;
let queryAllLevel = 0;

//-----------------------------------------------------------------------------
// Pseudo classes
//-----------------------------------------------------------------------------

/** @type {Map<string, PseudoClassPredicateBuilder>} */
const customPseudoClasses = new Map();

customPseudoClasses
    .set("contains", makePatternBasedPseudoClass("contains", getNodeText))
    .set("displayed", () => isNodeDisplayed)
    .set("empty", () => isEmpty)
    .set("eq", (strIndex) => {
        const index = $parseInt(strIndex);
        if (!$isInteger(index)) {
            throw selectorError("eq", `expected index to be an integer (got ${strIndex})`);
        }
        return index;
    })
    .set("first", () => 0)
    .set("focusable", () => isNodeFocusable)
    .set("has", (selector) => isNodeHaving.bind(null, selector))
    .set("hidden", () => isNodeHidden)
    .set("iframe", () => getNodeIframe)
    .set("interactive", () => isNodeInteractive)
    .set("last", () => -1)
    .set("not", (selector) => isNodeNotMatching.bind(null, selector))
    .set("only", () => isOnlyNode)
    .set("scrollable", (axis) => isNodeScrollable.bind(null, axis))
    .set("selected", () => isNodeSelected)
    .set("shadow", () => getNodeShadowRoot)
    .set("value", makePatternBasedPseudoClass("value", getNodeValue))
    .set("viewPort", () => isNodeInViewPort)
    .set("visible", () => isNodeVisible);

const rCustomPseudoClass = compilePseudoClassRegex();

//-----------------------------------------------------------------------------
// Internal exports (inside Hoot/Hoot-DOM)
//-----------------------------------------------------------------------------

export function cleanupDOM() {
    // Dimensions
    currentDimensions.width = innerWidth;
    currentDimensions.height = innerHeight;

    // Observers
    const remainingObservers = observers.size;
    if (remainingObservers) {
        for (const { observer } of observers.values()) {
            observer.disconnect();
        }
        observers.clear();
    }
}

/**
 * @param {Node | () => Node} node
 */
export function defineRootNode(node) {
    if (typeof node === "function") {
        getDefaultRoot = node;
    } else if (node) {
        getDefaultRoot = () => node;
    } else {
        getDefaultRoot = () => document;
    }
}

export function getCurrentDimensions() {
    return currentDimensions;
}

/**
 * @param {Node} [node]
 * @returns {Document}
 */
export function getDocument(node) {
    if (!node) {
        return document;
    }
    return isDocument(node) ? node : node.ownerDocument || document;
}

/**
 * @param {Node} node
 * @param {string} attribute
 * @returns {string | null}
 */
export function getNodeAttribute(node, attribute) {
    return node.getAttribute?.(attribute) ?? null;
}

/**
 * @param {Node} node
 * @returns {NodeValue}
 */
export function getNodeValue(node) {
    switch (node.type) {
        case "checkbox":
        case "radio":
            return node.checked;
        case "file":
            return [...node.files];
        case "number":
        case "range":
            return node.valueAsNumber;
        case "date":
        case "datetime-local":
        case "month":
        case "time":
        case "week":
            return node.valueAsDate.toISOString();
    }
    return node.value;
}

/**
 * @param {Node} node
 * @param {QueryRectOptions} [options]
 */
export function getNodeRect(node, options) {
    if (!isElement(node)) {
        return new DOMRect();
    }

    /** @type {DOMRect} */
    const rect = node.getBoundingClientRect();
    const parentFrame = getParentFrame(node);
    if (parentFrame) {
        const parentRect = getNodeRect(parentFrame);
        rect.x -= parentRect.x;
        rect.y -= parentRect.y;
    }

    if (!options?.trimPadding) {
        return rect;
    }

    const style = getStyle(node);
    const { x, y, width, height } = rect;
    const [pl, pr, pt, pb] = ["left", "right", "top", "bottom"].map((side) =>
        pixelValueToNumber(style.getPropertyValue(`padding-${side}`))
    );

    return new DOMRect(x + pl, y + pt, width - (pl + pr), height - (pt + pb));
}

/**
 * @param {Node} node
 * @param {QueryTextOptions} [options]
 * @returns {string}
 */
export function getNodeText(node, options) {
    let content;
    if (typeof node.innerText === "string") {
        content = node.innerText;
    } else {
        content = node.textContent;
    }
    if (!options?.raw) {
        content = content.replace(R_HORIZONTAL_WHITESPACE, " ").trim();
    }
    if (options?.inline) {
        content = content.replace(R_LINEBREAK, " ");
    }
    return content;
}

/**
 * @param {Node} node
 * @returns {Node | null}
 */
export function getInteractiveNode(node) {
    let currentEl = ensureElement(node);
    if (!currentEl) {
        return null;
    }
    while (currentEl && !isNodeInteractive(currentEl)) {
        currentEl = currentEl.parentElement;
    }
    return currentEl;
}

/**
 * @template {Node} T
 * @param {T} node
 * @returns {T extends Element ? CSSStyleDeclaration : null}
 */
export function getStyle(node) {
    return isElement(node) ? getComputedStyle(node) : null;
}

/**
 * @param {Node} [node]
 * @returns {Window}
 */
export function getWindow(node) {
    if (!node) {
        return window;
    }
    return isWindow(node) ? node : getDocument(node).defaultView;
}

/**
 * @param {Node} node
 * @returns {boolean}
 */
export function isCheckable(node) {
    switch (getTag(node)) {
        case "input":
            return node.type === "checkbox" || node.type === "radio";
        case "label":
            return isCheckable(node.control);
        default:
            return false;
    }
}

/**
 * @param {unknown} value
 * @returns {boolean}
 */
export function isEmpty(value) {
    if (!value) {
        return true;
    }
    if (typeof value === "object") {
        if (isNode(value)) {
            return isEmpty(getNodeContent(value));
        }
        if (!isIterable(value)) {
            value = $keys(value);
        }
        return [...value].length === 0;
    }
    return false;
}

/**
 * Returns whether the given object is an {@link EventTarget}.
 *
 * @template T
 * @param {T} object
 * @returns {T extends EventTarget ? true : false}
 * @example
 *  isEventTarget(window); // true
 * @example
 *  isEventTarget(new App()); // false
 */
export function isEventTarget(object) {
    return object && typeof object.addEventListener === "function";
}

/**
 * Returns whether the given object is a {@link Node} object.
 * Note that it is independant from the {@link Node} class itself to support
 * cross-window checks.
 *
 * @template T
 * @param {T} object
 * @returns {T extends Node ? true : false}
 */
export function isNode(object) {
    return object && typeof object.nodeType === "number" && typeof object.nodeName === "string";
}

/**
 * @param {Node} node
 */
export function isNodeCssVisible(node) {
    const element = ensureElement(node);
    if (element === getDefaultRoot() || isRootElement(element)) {
        return true;
    }
    const style = getStyle(element);
    if (style?.visibility === "hidden" || style?.opacity === "0") {
        return false;
    }
    const parent = element.parentNode;
    return !parent || isNodeCssVisible(isShadowRoot(parent) ? parent.host : parent);
}

/**
 * @param {Window | Node} node
 */
export function isNodeDisplayed(node) {
    const element = ensureElement(node);
    if (!isInDOM(element)) {
        return false;
    }
    if (isRootElement(element) || element.offsetParent || element.closest("svg")) {
        return true;
    }
    // `position=fixed` elements in Chrome do not have an `offsetParent`
    return !isFirefox() && getStyle(element)?.position === "fixed";
}

/**
 * @param {Node} node
 * @param {FocusableOptions} [options]
 */
export function isNodeFocusable(node, options) {
    return (
        isNodeDisplayed(node) &&
        node.matches?.(FOCUSABLE_SELECTOR) &&
        (!options?.tabbable || node.tabIndex >= 0)
    );
}

/**
 * @param {Window | Node} node
 */
export function isNodeInViewPort(node) {
    const element = ensureElement(node);
    const { x, y } = getNodeRect(element);

    return y > 0 && y < currentDimensions.height && x > 0 && x < currentDimensions.width;
}

/**
 * @param {ScrollAxis} axis
 * @param {Window | Node} node
 */
export function isNodeScrollable(axis, node) {
    if (!isElement(node)) {
        return false;
    }
    const isScrollableX = node.clientWidth < node.scrollWidth;
    const isScrollableY = node.clientHeight < node.scrollHeight;
    switch (axis) {
        case "both": {
            if (!isScrollableX || !isScrollableY) {
                return false;
            }
            break;
        }
        case "x": {
            if (!isScrollableX) {
                return false;
            }
            break;
        }
        case "y": {
            if (!isScrollableY) {
                return false;
            }
            break;
        }
        default: {
            // Check for any scrollable axis
            if (!isScrollableX && !isScrollableY) {
                return false;
            }
        }
    }
    const overflow = getStyle(node).getPropertyValue("overflow");
    if (R_SCROLLABLE_OVERFLOW.test(overflow)) {
        return true;
    }
    return false;
}

/**
 * @param {Window | Node} node
 */
export function isNodeVisible(node) {
    const element = ensureElement(node);

    // Must be displayed and not hidden by CSS
    if (!isNodeDisplayed(element) || !isNodeCssVisible(element)) {
        return false;
    }

    let visible = false;

    // Check size (width & height)
    const { width, height } = getNodeRect(element);
    visible = width > 0 && height > 0;

    // Check content (if display=contents)
    if (!visible && getStyle(element)?.display === "contents") {
        for (const child of element.childNodes) {
            if (isNodeVisible(child)) {
                return true;
            }
        }
    }

    return visible;
}

/**
 * @param {Dimensions} dimensions
 * @returns {[number, number]}
 */
export function parseDimensions(dimensions) {
    return parseNumberTuple(dimensions, ["width", "w"], ["height", "h"]);
}

/**
 * @param {Position} position
 * @returns {[number, number]}
 */
export function parsePosition(position) {
    return parseNumberTuple(
        position,
        ["x", "left", "clientX", "pageX", "screenX"],
        ["y", "top", "clientY", "pageY", "screenY"]
    );
}

/**
 * @param {number} width
 * @param {number} height
 */
export function setDimensions(width, height) {
    const defaultRoot = getDefaultRoot();
    if (!$isNaN(width)) {
        currentDimensions.width = width;
        defaultRoot.style?.setProperty("width", `${width}px`, "important");
    }
    if (!$isNaN(height)) {
        currentDimensions.height = height;
        defaultRoot.style?.setProperty("height", `${height}px`, "important");
    }
}

/**
 * @param {Node} node
 * @param {{ object?: boolean }} [options]
 * @returns {string | string[]}
 */
export function toSelector(node, options) {
    const parts = {
        tag: node.nodeName.toLowerCase(),
    };
    if (node.id) {
        parts.id = `#${node.id}`;
    }
    if (node.classList?.length) {
        parts.class = `.${[...node.classList].join(".")}`;
    }
    return options?.object ? parts : $values(parts).join("");
}

// Following selector is based on this spec:
// https://html.spec.whatwg.org/multipage/interaction.html#dom-tabindex
export const FOCUSABLE_SELECTOR = [
    "a[href]",
    "area[href]",
    "button:enabled",
    "details > summary:first-of-type",
    "iframe",
    "input:enabled",
    "select:enabled",
    "textarea:enabled",
    "[tabindex]",
    "[contenteditable=true]",
].join(",");

//-----------------------------------------------------------------------------
// Exports
//-----------------------------------------------------------------------------

/**
 * Returns a standardized representation of the given `string` value as a human-readable
 * XML string template (or HTML if the `type` option is `"html"`).
 *
 * @param {string} value
 * @param {FormatXmlOptions} [options]
 * @returns {string}
 */
export function formatXml(value, options) {
    const nodes = parseXml(value, options?.type || "xml");
    const layers = extractLayers(nodes, 0, options?.keepInlineTextNodes ?? false);
    return generateStringFromLayers(layers, options?.tabSize ?? 4);
}

/**
 * Returns the active element in the given document. Further checks are performed
 * in the following cases:
 * - the given node is an iframe (checks in its content document);
 * - the given node has a shadow root (checks in that shadow root document);
 * - the given node is the body of an iframe (checks in the parent document).
 *
 * @param {Node} [node]
 */
export function getActiveElement(node) {
    const doc = getDocument(node);
    const view = doc.defaultView;
    const { activeElement } = doc;
    const { contentDocument, shadowRoot } = activeElement;

    if (contentDocument && contentDocument.activeElement !== contentDocument.body) {
        // Active element is an "iframe" element (with an active element other than its own body):
        if (contentDocument.activeElement === contentDocument.body) {
            // Active element is the body of the iframe:
            // -> returns that element
            return contentDocument.activeElement;
        } else {
            // Active element is something else than the body:
            // -> get the active element inside the iframe document
            return getActiveElement(contentDocument);
        }
    }

    if (shadowRoot) {
        // Active element has a shadow root:
        // -> get the active element inside its root
        return shadowRoot.activeElement;
    }

    if (activeElement === doc.body && view !== view.parent) {
        // Active element is the body of an iframe:
        // -> get the active element of its parent frame (recursively)
        return getActiveElement(view.parent.document);
    }

    return activeElement;
}

/**
 * Returns the list of focusable elements in the given parent, sorted by their `tabIndex`
 * property.
 *
 * @see {@link isFocusable} for more information
 * @param {FocusableOptions} [options]
 * @returns {Element[]}
 * @example
 *  getFocusableElements();
 */
export function getFocusableElements(options) {
    const parent = _queryOne(options?.root || getDefaultRoot());
    if (typeof parent.querySelectorAll !== "function") {
        return [];
    }
    const byTabIndex = {};
    for (const element of parent.querySelectorAll(FOCUSABLE_SELECTOR)) {
        const { tabIndex } = element;
        if ((options?.tabbable && tabIndex < 0) || !isNodeDisplayed(element)) {
            continue;
        }
        if (!byTabIndex[tabIndex]) {
            byTabIndex[tabIndex] = [];
        }
        byTabIndex[tabIndex].push(element);
    }
    const withTabIndexZero = byTabIndex[0] || [];
    delete byTabIndex[0];
    return [...$values(byTabIndex).flat(), ...withTabIndexZero];
}

/**
 * Returns the next focusable element after the current active element if it is
 * contained in the given parent.
 *
 * @see {@link getFocusableElements}
 * @param {FocusableOptions} [options]
 * @returns {Element | null}
 * @example
 *  getPreviousFocusableElement();
 */
export function getNextFocusableElement(options) {
    const parent = _queryOne(options?.root || getDefaultRoot());
    const focusableEls = getFocusableElements({ ...options, parent });
    const index = focusableEls.indexOf(getActiveElement(parent));
    return focusableEls[index + 1] || null;
}

/**
 * Returns the parent `<iframe>` of a given node (if any).
 *
 * @param {Node} node
 * @returns {HTMLIFrameElement | null}
 */
export function getParentFrame(node) {
    const doc = getDocument(node);
    if (!doc) {
        return null;
    }
    const view = doc.defaultView;
    if (view !== view.parent) {
        for (const iframe of view.parent.document.getElementsByTagName("iframe")) {
            if (iframe.contentWindow === view) {
                return iframe;
            }
        }
    }
    return null;
}

/**
 * Returns the previous focusable element before the current active element if it is
 * contained in the given parent.
 *
 * @see {@link getFocusableElements}
 * @param {FocusableOptions} [options]
 * @returns {Element | null}
 * @example
 *  getPreviousFocusableElement();
 */
export function getPreviousFocusableElement(options) {
    const parent = _queryOne(options?.root || getDefaultRoot());
    const focusableEls = getFocusableElements({ ...options, parent });
    const index = focusableEls.indexOf(getActiveElement(parent));
    return index < 0 ? focusableEls.at(-1) : focusableEls[index - 1] || null;
}

/**
 * Checks whether a target is displayed, meaning that it has an offset parent and
 * is contained in the current document.
 *
 * Note that it does not mean that the target is "visible" (it can still be hidden
 * by CSS properties such as `width`, `opacity`, `visiblity`, etc.).
 *
 * @param {Target} target
 * @returns {boolean}
 */
export function isDisplayed(target) {
    return _guardedQueryAll(target, { displayed: true }).length > 0;
}

/**
 * Returns whether the given node is editable, meaning that it is an `":enabled"`
 * `<input>` or `<textarea>` {@link Element};
 *
 * Note: this does **NOT** support elements with `contenteditable="true"`.
 *
 * @param {Node} node
 * @returns {boolean}
 * @example
 *  isEditable(document.querySelector("input")); // true
 * @example
 *  isEditable(document.body); // false
 */
export function isEditable(node) {
    return (
        isElement(node) &&
        !node.matches?.(":disabled") &&
        ["input", "textarea"].includes(getTag(node))
    );
}

/**
 * Returns whether an element is focusable. Focusable elements are either:
 * - `<a>` or `<area>` elements with an `href` attribute;
 * - *enabled* `<button>`, `<input>`, `<select>` and `<textarea>` elements;
 * - `<iframe>` elements;
 * - any element with its `contenteditable` attribute set to `"true"`.
 *
 * A focusable element must also not have a `tabIndex` property set to less than 0.
 *
 * @see {@link FOCUSABLE_SELECTOR}
 * @param {Target} target
 * @returns {boolean}
 */
export function isFocusable(target) {
    return _guardedQueryAll(target, { focusable: true }).length > 0;
}

/**
 * Returns whether the given target is contained in the current root document.
 *
 * @param {Window | Node} target
 * @returns {boolean}
 * @example
 *  isInDOM(queryFirst("div")); // true
 * @example
 *  isInDOM(document.createElement("div")); // Not attached -> false
 */
export function isInDOM(target) {
    return ensureElement(target)?.isConnected;
}

/**
 * Checks whether a target is *at least partially* visible in the current viewport.
 *
 * @param {Target} target
 * @returns {boolean}
 */
export function isInViewPort(target) {
    return _guardedQueryAll(target, { viewPort: true }).length > 0;
}

/**
 * Returns whether an element is scrollable.
 *
 * @param {Target} target
 * @param {ScrollAxis} [axis]
 * @returns {boolean}
 */
export function isScrollable(target, axis) {
    return _guardedQueryAll(target, { scrollable: axis }).length > 0;
}

/**
 * Checks whether a target is visible, meaning that it is "displayed" (see {@link isDisplayed}),
 * has a non-zero width and height, and is not hidden by "opacity" or "visibility"
 * CSS properties.
 *
 * Note that it does not account for:
 *  - the position of the target in the viewport (e.g. negative x/y coordinates)
 *  - the color of the target (e.g. transparent text with no background).
 *
 * @param {Target} target
 * @returns {boolean}
 */
export function isVisible(target) {
    return _guardedQueryAll(target, { visible: true }).length > 0;
}

/**
 * Equivalent to the native `node.matches(selector)`, with a few differences:
 * - it can take any {@link Target} (strings, nodes and iterable of nodes);
 * - it supports custom pseudo-classes, such as ":contains" or ":visible".
 *
 * @param {Target} target
 * @param {string} selector
 * @returns {boolean}
 * @example
 *  matches("input[name=surname]", ":value(John)");
 * @example
 *  matches(buttonEl, ":contains(Submit)");
 */
export function matches(target, selector) {
    return elementsMatch(_guardedQueryAll(target), selector);
}

/**
 * Listens for DOM mutations on a given target.
 *
 * This helper has 2 main advantages over directly calling the native MutationObserver:
 * - it ensures a single observer is created for a given target, even if multiple
 *  callbacks are registered;
 * - it keeps track of these observers, which allows to check whether an observer
 *  is still running while it should not, and to disconnect all running observers
 *  at once.
 *
 * @param {HTMLElement} target
 * @param {MutationCallback} callback
 */
export function observe(target, callback) {
    if (observers.has(target)) {
        observers.get(target).callbacks.add(callback);
    } else {
        const callbacks = new Set([callback]);
        const observer = new MutationObserver((mutations, observer) => {
            for (const callback of callbacks) {
                callback(mutations, observer);
            }
        });
        observer.observe(target, {
            attributes: true,
            characterData: true,
            childList: true,
            subtree: true,
        });
        observers.set(target, { callbacks, observer });
    }

    return function disconnect() {
        if (!observers.has(target)) {
            return;
        }
        const { callbacks, observer } = observers.get(target);
        callbacks.delete(callback);
        if (!callbacks.size) {
            observer.disconnect();
            observers.delete(target);
        }
    };
}

/**
 * Returns a list of nodes matching the given {@link Target}.
 * This function can either be used as a **template literal tag** (only supports
 * string selector without options) or invoked the usual way.
 *
 * The target can be:
 * - a {@link Node} (or an iterable of nodes), or {@link Window} object;
 * - a {@link Document} object (which will be converted to its body);
 * - a string representing a *custom selector* (which will be queried in the `root` option);
 *
 * This function allows all string selectors supported by the native {@link Element.querySelector}
 * along with some additional custom pseudo-classes:
 *
 * - `:contains(text)`: matches nodes whose *content* matches the given *text*;
 *      * given *text* supports regular expression syntax (e.g. `:contains(/^foo.+/)`)
 *          and is case-insensitive;
 *      * given *text* will be matched against:
 *          - an `<input>`, `<textarea>` or `<select>` element's **value**;
 *          - or any other element's **inner text**.
 * - `:displayed`: matches nodes that are "displayed" (see {@link isDisplayed});
 * - `:empty`: matches nodes that have an empty *content* (**value** or **inner text**);
 * - `:eq(n)`: matches the *nth* node (0-based index);
 * - `:first`: matches the first node matching the selector (regardless of its actual
 *  DOM siblings);
 * - `:focusable`: matches nodes that can be focused (see {@link isFocusable});
 * - `:hidden`: matches nodes that are **not** "visible" (see {@link isVisible});
 * - `:interactive`: matches nodes that are not affected by 'pointer-events: none'
 * - `:iframe`: matches nodes that are `<iframe>` elements, and returns their `body`
 *  if it is ready;
 * - `:last`: matches the last node matching the selector (regardless of its actual
 *  DOM siblings);
 * - `:selected`: matches nodes that are selected (e.g. `<option>` elements);
 * - `:shadow`: matches nodes that have shadow roots, and returns their shadow root;
 * - `:scrollable(axis)`: matches nodes that are scrollable (see {@link isScrollable});
 * - `:viewPort`: matches nodes that are contained in the current view port (see
 *  {@link isInViewPort});
 * - `:visible`: matches nodes that are "visible" (see {@link isVisible});
 *
 * An `options` object can be specified to filter[1] the results:
 * - `displayed`: whether the nodes must be "displayed" (see {@link isDisplayed});
 * - `exact`: the exact number of nodes to match (throws an error if the number of
 *  nodes doesn't match);
 * - `focusable`: whether the nodes must be "focusable" (see {@link isFocusable});
 * - `root`: the root node to query the selector in (defaults to the current fixture);
 * - `viewPort`: whether the nodes must be partially visible in the current viewport
 *  (see {@link isInViewPort});
 * - `visible`: whether the nodes must be "visible" (see {@link isVisible}).
 *      * This option implies `displayed`
 *
 * [1] these filters (except for `exact` and `root`) achieve the same result as
 *  using their homonym pseudo-classes on the final group of the given selector
 *  string (e.g. ```queryAll`ul > li:visible`;``` = ```queryAll("ul > li", { visible: true })```).
 *
 * @param {Target} target
 * @param {QueryOptions} [options]
 * @returns {Element[]}
 * @example
 *  // regular selectors
 *  queryAll`window`; // -> []
 *  queryAll`input#name`; // -> [input]
 *  queryAll`div`; // -> [div, div, ...]
 *  queryAll`ul > li`; // -> [li, li, ...]
 * @example
 *  // custom selectors
 *  queryAll`div:visible:contains(Lorem ipsum)`; // -> [div, div, ...]
 *  queryAll`div:visible:contains(${/^L\w+\si.*m$/})`; // -> [div, div, ...]
 *  queryAll`:focusable`; // -> [a, button, input, ...]
 *  queryAll`.o_iframe:iframe p`; // -> [p, p, ...] (inside iframe)
 *  queryAll`#editor:shadow div`; // -> [div, div, ...] (inside shadow DOM)
 * @example
 *  // with options
 *  queryAll(`div:first`, { exact: 1 }); // -> [div]
 *  queryAll(`div`, { root: queryOne`iframe` }); // -> [div, div, ...]
 *  // redundant, but possible
 *  queryAll(`button:visible`, { visible: true }); // -> [button, button, ...]
 */
export function queryAll(target, options) {
    [target, options] = parseRawArgs(arguments);
    return _guardedQueryAll(target, options);
}

/**
 * Performs a {@link queryAll} with the given arguments and returns a list of the
 * *attribute values* of the matching nodes.
 *
 * @param {Target} target
 * @param {string} attribute
 * @param {QueryOptions} [options]
 * @returns {string[]}
 */
export function queryAllAttributes(target, attribute, options) {
    return _guardedQueryAll(target, options).map((node) => getNodeAttribute(node, attribute));
}

/**
 * Performs a {@link queryAll} with the given arguments and returns a list of the
 * *properties* of the matching nodes.
 *
 * @param {Target} target
 * @param {string} property
 * @param {QueryOptions} [options]
 * @returns {any[]}
 */
export function queryAllProperties(target, property, options) {
    return _guardedQueryAll(target, options).map((node) => node[property]);
}

/**
 * Performs a {@link queryAll} with the given arguments and returns a list of the
 * {@link DOMRect} of the matching nodes.
 *
 * There are a few differences with the native {@link Element.getBoundingClientRect}:
 * - rects take their positions relative to the top window element (instead of their
 *  parent `<iframe>` if any);
 * - they can be trimmed to remove padding with the `trimPadding` option.
 *
 * @param {Target} target
 * @param {QueryOptions & QueryRectOptions} [options]
 * @returns {DOMRect[]}
 */
export function queryAllRects(target, options) {
    [target, options] = parseRawArgs(arguments);
    return _guardedQueryAll(target, options).map(getNodeRect);
}

/**
 * Performs a {@link queryAll} with the given arguments and returns a list of the
 * *texts* of the matching nodes.
 *
 * @param {Target} target
 * @param {QueryOptions & QueryTextOptions} [options]
 * @returns {string[]}
 */
export function queryAllTexts(target, options) {
    [target, options] = parseRawArgs(arguments);
    return _guardedQueryAll(target, options).map((node) => getNodeText(node, options));
}

/**
 * Performs a {@link queryAll} with the given arguments and returns a list of the
 * *values* of the matching nodes.
 *
 * @param {Target} target
 * @param {QueryOptions} [options]
 * @returns {NodeValue[]}
 */
export function queryAllValues(target, options) {
    [target, options] = parseRawArgs(arguments);
    return _guardedQueryAll(target, options).map(getNodeValue);
}

/**
 * Performs a {@link queryOne} with the given arguments, with a default 'first'
 * option, to ensure that *at least* one element is returned.
 *
 * 'first' can be overridden by 'last' or 'eq' if needed.
 *
 * @param {Target} target
 * @param {QueryOptions} [options]
 * @returns {Node}
 */
export function queryAny(target, options) {
    [target, options] = parseRawArgs(arguments);
    return _queryOne(target, ensureCount(options));
}

/**
 * Performs a {@link queryOne} with the given arguments and returns the value of
 * the given *attribute* of the matching node.
 *
 * @param {Target} target
 * @param {string} attribute
 * @param {QueryOptions} [options]
 * @returns {string | null}
 */
export function queryAttribute(target, attribute, options) {
    return getNodeAttribute(_queryOne(target, options), attribute);
}

/**
 * Performs a {@link queryAll} with the given arguments and returns the first result
 * or `null`.
 *
 * @param {Target} target
 * @param {QueryOptions} options
 * @returns {Element | null}
 */
export function queryFirst(target, options) {
    [target, options] = parseRawArgs(arguments);
    return _guardedQueryAll(target, options)[0] || null;
}

/**
 * Performs a {@link queryAll} with the given arguments, along with a forced `exact: 1`
 * option to ensure only one node matches the given {@link Target}.
 *
 * The returned value is a single node instead of a list of nodes.
 *
 * @param {Target} target
 * @param {Omit<QueryOptions, "exact">} [options]
 * @returns {Element}
 */
export function queryOne(target, options) {
    [target, options] = parseRawArgs(arguments);
    if ($isInteger(options?.exact)) {
        throw new HootDomError(
            `cannot call \`queryOne\` with 'exact'=${options.exact}: did you mean to use \`queryAll\`?`
        );
    }
    return _queryOne(target, options);
}

/**
 * Performs a {@link queryOne} with the given arguments and returns the {@link DOMRect}
 * of the matching node.
 *
 * There are a few differences with the native {@link Element.getBoundingClientRect}:
 * - rects take their positions relative to the top window element (instead of their
 *  parent `<iframe>` if any);
 * - they can be trimmed to remove padding with the `trimPadding` option.
 *
 * @param {Target} target
 * @param {QueryOptions & QueryRectOptions} [options]
 * @returns {DOMRect}
 */
export function queryRect(target, options) {
    [target, options] = parseRawArgs(arguments);
    return getNodeRect(_queryOne(target, options), options);
}

/**
 * Performs a {@link queryOne} with the given arguments and returns the *text* of
 * the matching node.
 *
 * @param {Target} target
 * @param {QueryOptions & QueryTextOptions} [options]
 * @returns {string}
 */
export function queryText(target, options) {
    [target, options] = parseRawArgs(arguments);
    return getNodeText(_queryOne(target, options), options);
}

/**
 * Performs a {@link queryOne} with the given arguments and returns the *value* of
 * the matching node.
 *
 * @param {Target} target
 * @param {QueryOptions} [options]
 * @returns {NodeValue}
 */
export function queryValue(target, options) {
    [target, options] = parseRawArgs(arguments);
    return getNodeValue(_queryOne(target, options));
}

/**
 * Combination of {@link queryAll} and {@link waitUntil}: waits for a given target
 * to match elements in the DOM and returns the first matching node when it appears
 * (or immediately if it is already present).
 *
 * @see {@link queryAll}
 * @see {@link waitUntil}
 * @param {Target} target
 * @param {QueryOptions & WaitOptions} [options]
 * @returns {Promise<Element>}
 * @example
 *  const button = await waitFor(`button`);
 *  button.click();
 */
export function waitFor(target, options) {
    [target, options] = parseRawArgs(arguments);
    return waitUntil(_waitForFirst.bind(null, target, options), {
        message: getWaitForMessage,
        ...options,
    });
}

/**
 * Opposite of {@link waitFor}: waits for a given target to disappear from the DOM
 * (resolves instantly if the selector is already missing).
 *
 * @see {@link waitFor}
 * @param {Target} target
 * @param {QueryOptions & WaitOptions} [options]
 * @returns {Promise<number>}
 * @example
 *  await waitForNone(`button`);
 */
export function waitForNone(target, options) {
    [target, options] = parseRawArgs(arguments);
    return waitUntil(_waitForNone.bind(null, target, options), {
        message: getWaitForNoneMessage,
        ...options,
    });
}
