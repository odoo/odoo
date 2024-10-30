/** @odoo-module */

import { HootDomError, getTag, isFirefox, isIterable, parseRegExp } from "../hoot_dom_utils";
import { Deferred, waitUntil } from "./time";

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
 * @typedef {(content: string) => (node: Node, index: number, nodes: Node[]) => boolean | Node} PseudoClassPredicateBuilder
 *
 * @typedef {{
 *  displayed?: boolean;
 *  exact?: number;
 *  root?: HTMLElement;
 *  viewPort?: boolean;
 *  visible?: boolean;
 * }} QueryOptions
 *
 * @typedef {{
 *  trimPadding?: boolean;
 * }} QueryRectOptions
 *
 * @typedef {{
 *  raw?: boolean;
 * }} QueryTextOptions
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
    Boolean,
    document,
    DOMParser,
    innerWidth,
    innerHeight,
    Map,
    MutationObserver,
    Number: { isInteger: $isInteger, isNaN: $isNaN, parseInt: $parseInt, parseFloat: $parseFloat },
    Object: { keys: $keys, values: $values },
    RegExp,
    Set,
} = globalThis;

//-----------------------------------------------------------------------------
// Internal
//-----------------------------------------------------------------------------

/**
 * @param  {string[]} values
 */
const and = (values) => {
    const last = values.pop();
    if (values.length) {
        return [values.join(", "), last].join(" and ");
    } else {
        return last;
    }
};

const compilePseudoClassRegex = () => {
    const customKeys = [...customPseudoClasses.keys()].filter((k) => k !== "has" && k !== "not");
    return new RegExp(`:(${customKeys.join("|")})`);
};

/**
 * @param {Element[]} elements
 * @param {string} selector
 */
const elementsMatch = (elements, selector) => {
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
};

/**
 * @param {Node} node
 * @returns {Element | null}
 */
const ensureElement = (node) => {
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
};

/**
 * @param {Iterable<Node>} nodes
 * @param {number} level
 * @param {boolean} [keepInlineTextNodes]
 */
const extractLayers = (nodes, level, keepInlineTextNodes) => {
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
};

/**
 * @param {Iterable<Node>} nodesToFilter
 */
const filterUniqueNodes = (nodesToFilter) => {
    /** @type {Node[]} */
    const nodes = [];
    for (const node of nodesToFilter) {
        if (isQueryableNode(node) && !nodes.includes(node)) {
            nodes.push(node);
        }
    }
    return nodes;
};

/**
 * @param {MarkupLayer[]} layers
 * @param {number} tabSize
 */
const generateStringFromLayers = (layers, tabSize) => {
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
};

/**
 * @param {Node} node
 * @returns {NodeValue}
 */
const getNodeContent = (node) => {
    switch (getTag(node)) {
        case "input":
        case "option":
        case "textarea":
            return getNodeValue(node);
        case "select":
            return [...node.selectedOptions].map(getNodeValue).join(",");
    }
    return getNodeText(node);
};

/**
 * @param {string} string
 */
const getStringContent = (string) => string.match(R_QUOTE_CONTENT)?.[2] || string;

/**
 * @param {string} [char]
 */
const isChar = (char) => Boolean(char) && R_CHAR.test(char);

/**
 * @template T
 * @param {T} object
 * @returns {T extends Document ? true : false}
 */
const isDocument = (object) => object?.nodeType === Node.DOCUMENT_NODE;

/**
 * @template T
 * @param {T} object
 * @returns {T extends Element ? true: false}
 */
const isElement = (object) => object?.nodeType === Node.ELEMENT_NODE;

/**
 * @param {Node} node
 */
const isQueryableNode = (node) => QUERYABLE_NODE_TYPES.includes(node.nodeType);

/**
 * @param {Element} [el]
 */
const isRootElement = (el) => el && R_ROOT_ELEMENT.test(el.nodeName || "");

/**
 * @param {Element} el
 */
const isShadowRoot = (el) => el.nodeType === Node.DOCUMENT_FRAGMENT_NODE && Boolean(el.host);

/**
 * @template T
 * @param {T} object
 * @returns {T extends Window ? true : false}
 */
const isWindow = (object) => object?.window === object && object.constructor.name === "Window";

/**
 * @param {string} [char]
 */
const isWhiteSpace = (char) => Boolean(char) && R_HORIZONTAL_WHITESPACE.test(char);

/**
 * @param {string} pseudoClass
 * @param {(node: Node) => NodeValue} getContent
 */
const makePatternBasedPseudoClass = (pseudoClass, getContent) => {
    return (content) => {
        let regex;
        try {
            regex = parseRegExp(content);
        } catch (err) {
            throw selectorError(pseudoClass, err.message);
        }
        if (regex instanceof RegExp) {
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
};

/**
 *
 * @param {string | (node: Node, index: number, nodes: Node[]) => boolean} filter
 * @param {Node} node
 * @param {number} index
 * @param {Node[]} allNodes
 * @returns
 */
const matchFilter = (filter, nodes, index) => {
    const node = nodes[index];
    if (typeof filter === "function") {
        return filter(node, index, nodes);
    } else {
        return node.matches?.(String(filter));
    }
};

/**
 * @param {string} query
 * @param {number} width
 * @param {number} height
 */
const matchesQuery = (query, width, height) =>
    query
        .toLowerCase()
        .split(/\s*,\s*/)
        .some((orPart) =>
            orPart
                .split(/\s*\band\b\s*/)
                .every((andPart) => matchesQueryPart(andPart, width, height))
        );

/**
 * @param {string} query
 * @param {number} width
 * @param {number} height
 */
const matchesQueryPart = (query, width, height) => {
    const [, key, value] = query.match(/\(\s*([\w-]+)\s*:\s*(.+)\s*\)/) || [];
    let result = false;
    if (key) {
        switch (key) {
            case "display-mode": {
                result = value === mockedMatchMedia.DISPLAY_MODE;
                break;
            }
            case "max-height": {
                result = height <= $parseFloat(value);
                break;
            }
            case "max-width": {
                result = width <= $parseFloat(value);
                break;
            }
            case "min-height": {
                result = height >= $parseFloat(value);
                break;
            }
            case "min-width": {
                result = width >= $parseFloat(value);
                break;
            }
            case "orientation": {
                result = value === "landscape" ? width > height : width < height;
                break;
            }
            case "pointer": {
                switch (value) {
                    case "coarse": {
                        result = globalThis.ontouchstart !== undefined;
                        break;
                    }
                    case "fine": {
                        result = globalThis.ontouchstart === undefined;
                        break;
                    }
                }
                break;
            }
            case "prefers-color-scheme": {
                result = value === mockedMatchMedia.COLOR_SCHEME;
                break;
            }
            case "prefers-reduced-motion": {
                result = value === mockedMatchMedia.REDUCED_MOTION;
                break;
            }
        }
    }

    return query.startsWith("not") ? !result : result;
};

/**
 * @template T
 * @param {T} value
 * @param {(keyof T)[]} propsA
 * @param {(keyof T)[]} propsB
 * @returns {[number, number]}
 */
const parseNumberTuple = (value, propsA, propsB) => {
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
};

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
const parseSelector = (selector) => {
    /**
     * @param {string} selector
     */
    const addToSelector = (selector) => {
        registerChar = false;
        const index = currentPart.length - 1;
        if (typeof currentPart[index] === "string") {
            currentPart[index] += selector;
        } else {
            currentPart.push(selector);
        }
    };

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
                currentPart.push(makeFilter(getStringContent(content)));
                currentPseudo = null;
            } else if (registerChar) {
                currentPseudo[1] += selector[i];
            }
        } else if (registerChar) {
            addToSelector(selector[i]);
        }
    }

    return groups;
};

/**
 * @param {string} xmlString
 * @param {"html" | "xml"} type
 */
const parseXml = (xmlString, type) => {
    const wrapperTag = type === "html" ? "body" : "templates";
    const document = parser.parseFromString(
        `<${wrapperTag}>${xmlString}</${wrapperTag}>`,
        `text/${type}`
    );
    if (document.getElementsByTagName("parsererror").length) {
        const trimmed = xmlString.length > 80 ? xmlString.slice(0, 80) + "…" : xmlString;
        throw new HootDomError(
            `error while parsing ${trimmed}: ${getNodeText(
                document.getElementsByTagName("parsererror")[0]
            )}`
        );
    }
    return document.getElementsByTagName(wrapperTag)[0].childNodes;
};

/**
 * Converts a CSS pixel value to a number, removing the 'px' part.
 *
 * @param {string} val
 */
const pixelValueToNumber = (val) => $parseFloat(val.endsWith("px") ? val.slice(0, -2) : val);

/**
 * @param {Node[]} nodes
 * @param {string} selector
 */
const queryWithCustomSelector = (nodes, selector) => {
    const selectorGroups = parseSelector(selector);
    const foundNodes = [];
    for (const selectorParts of selectorGroups) {
        let groupNodes = nodes;
        for (const [partSelector, ...filters] of selectorParts) {
            let baseSelector = partSelector;
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

            // Retrieve matching nodes and apply filters
            const getNodes = nodeGetter || DESCENDANTS;
            let currentGroupNodes = groupNodes.flatMap((node) => getNodes(node, baseSelector));

            // Filter/replace nodes based on custom pseudo-classes
            const pseudosReturningNode = new Set();
            for (const filter of filters) {
                const filteredGroupNodes = [];
                for (let i = 0; i < currentGroupNodes.length; i++) {
                    const result = matchFilter(filter, currentGroupNodes, i);
                    if (result === true) {
                        filteredGroupNodes.push(currentGroupNodes[i]);
                    } else if (result) {
                        filteredGroupNodes.push(result);
                        pseudosReturningNode.add(filter.name);
                    }
                }

                if (pseudosReturningNode.size > 1) {
                    const pseudoList = [...pseudosReturningNode];
                    throw selectorError(
                        pseudoList[0],
                        `cannot use multiple pseudo-classes returning nodes (${and(pseudoList)})`
                    );
                }

                currentGroupNodes = filteredGroupNodes;
            }

            groupNodes = currentGroupNodes;
        }

        foundNodes.push(...groupNodes);
    }

    return filterUniqueNodes(foundNodes);
};

/**
 * @param {string} pseudoClass
 * @param {string} message
 */
const selectorError = (pseudoClass, message) =>
    new HootDomError(`invalid selector \`:${pseudoClass}\`: ${message}`);

// Regexes
const R_CHAR = /[\w-]/;
const R_QUOTE_CONTENT = /^\s*(['"])?([^]*?)\1\s*$/;
const R_ROOT_ELEMENT = /^(HTML|HEAD|BODY)$/;
/**
 * \s without \n and \v
 */
const R_HORIZONTAL_WHITESPACE =
    /[\r\t\f \u00a0\u1680\u2000-\u200a\u2028\u2029\u202f\u205f\u3000\ufeff]+/g;

const QUERYABLE_NODE_TYPES = [Node.ELEMENT_NODE, Node.DOCUMENT_NODE, Node.DOCUMENT_FRAGMENT_NODE];

const parser = new DOMParser();

// Node getters

/** @type {NodeGetter} */
const DIRECT_CHILDREN = (node, selector) => {
    const children = [];
    for (const childNode of node.childNodes) {
        if (childNode.matches?.(selector)) {
            children.push(childNode);
        }
    }
    return children;
};

/** @type {NodeGetter} */
const DESCENDANTS = (node, selector) => [...(node.querySelectorAll?.(selector || "*") || [])];

/** @type {NodeGetter} */
const NEXT_SIBLING = (node, selector) => {
    const sibling = node.nextElementSibling;
    return sibling?.matches?.(selector) ? [sibling] : [];
};

/** @type {NodeGetter} */
const NEXT_SIBLINGS = (node, selector) => {
    const siblings = [];
    while ((node = node.nextElementSibling)) {
        if (node.matches?.(selector)) {
            siblings.push(node);
        }
    }
    return siblings;
};

/** @type {Map<HTMLElement, { callbacks: Set<MutationCallback>, observer: MutationObserver }>} */
const observers = new Map();
const currentDimensions = {
    width: innerWidth,
    height: innerHeight,
};
let getDefaultRoot = () => document;

//-----------------------------------------------------------------------------
// Pseudo classes
//-----------------------------------------------------------------------------

/** @type {Map<string, PseudoClassPredicateBuilder>} */
const customPseudoClasses = new Map();

customPseudoClasses
    .set("contains", makePatternBasedPseudoClass("contains", getNodeText))
    .set("displayed", () => {
        return function displayed(node) {
            return isNodeDisplayed(node);
        };
    })
    .set("empty", () => {
        return function empty(node) {
            return isEmpty(node);
        };
    })
    .set("eq", (content) => {
        const index = $parseInt(content);
        if (!$isInteger(index)) {
            throw selectorError("eq", `expected index to be an integer (got ${content})`);
        }
        return function eq(node, i, nodes) {
            return index < 0 ? i === nodes.length + index : i === index;
        };
    })
    .set("first", () => {
        return function first(node, i) {
            return i === 0;
        };
    })
    .set("focusable", () => {
        return function focusable(node) {
            return isNodeFocusable(node);
        };
    })
    .set("has", (content) => {
        return function has(node) {
            return Boolean(queryAll(content, { root: node }).length);
        };
    })
    .set("hidden", () => {
        return function hidden(node) {
            return !isNodeVisible(node);
        };
    })
    .set("iframe", () => {
        return function iframe(node) {
            // Note: should only apply on `iframe` elements
            /** @see parseSelector */
            const doc = node.contentDocument;
            return doc && doc.readyState !== "loading" ? doc : false;
        };
    })
    .set("last", () => {
        return function last(node, i, nodes) {
            return i === nodes.length - 1;
        };
    })
    .set("not", (content) => {
        return function not(node) {
            return !matches(node, content);
        };
    })
    .set("only", () => {
        return function only(node, i, nodes) {
            return nodes.length === 1;
        };
    })
    .set("scrollable", () => {
        return function scrollable(node) {
            return isNodeScrollable(node);
        };
    })
    .set("selected", () => {
        return function selected(node) {
            return Boolean(node.selected);
        };
    })
    .set("shadow", () => {
        return function shadow(node) {
            return node.shadowRoot || false;
        };
    })
    .set("value", makePatternBasedPseudoClass("value", getNodeValue))
    .set("visible", () => {
        return function visible(node) {
            return isNodeVisible(node);
        };
    });

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

export function getDefaultRootNode() {
    return getDefaultRoot();
}

/**
 * @param {Node} [node]
 * @returns {Document}
 */
export function getDocument(node) {
    node ||= getDefaultRoot();
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
    if (options?.raw) {
        return content;
    }
    return content.replace(R_HORIZONTAL_WHITESPACE, " ").trim();
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
    return getDocument(node).defaultView;
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
 * @param {FocusableOptions} node
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
 * @param {Window | Node} node
 * @param {"x" | "y"} [axis]
 */
export function isNodeScrollable(node, axis) {
    if (!isElement(node)) {
        return false;
    }
    const [scrollProp, sizeProp] =
        axis === "x" ? ["scrollWidth", "clientWidth"] : ["scrollHeight", "clientHeight"];
    if (node[scrollProp] > node[sizeProp]) {
        const overflow = getStyle(node).getPropertyValue("overflow");
        if (/\bauto\b|\bscroll\b/.test(overflow)) {
            return true;
        }
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
 * @type {typeof matchMedia}
 */
export function mockedMatchMedia(query) {
    let onchange = null;
    return {
        addEventListener: (type, callback) => window.addEventListener("resize", callback),
        get matches() {
            return matchesQuery(query, window.innerWidth, window.innerHeight);
        },
        media: query,
        get onchange() {
            return onchange;
        },
        set onchange(value) {
            value ||= null;
            if (value) {
                window.addEventListener("resize", value);
            } else {
                window.removeEventListener("resize", onchange);
            }
            onchange = value;
        },
        removeEventListener: (type, callback) => window.removeEventListener("resize", callback),
    };
}

mockedMatchMedia.COLOR_SCHEME = "light";
mockedMatchMedia.DISPLAY_MODE = "browser";
mockedMatchMedia.REDUCED_MOTION = "reduce";

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
 * Returns the active element in the given document (or in the owner document of
 * the given node).
 *
 * @param {Node} [node]
 */
export function getActiveElement(node) {
    const { activeElement } = getDocument(node);
    if (activeElement.contentDocument) {
        return getActiveElement(activeElement.contentDocument);
    }
    if (activeElement.shadowRoot) {
        return activeElement.shadowRoot.activeElement;
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
    const parent = queryOne(options?.root || getDefaultRoot());
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
    const parent = queryOne(options?.root || getDefaultRoot());
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
    const nodeDocument = node.ownerDocument;
    const view = nodeDocument.defaultView;
    if (view !== view.parent) {
        for (const iframe of view.parent.document.getElementsByTagName("iframe")) {
            if (iframe.contentDocument === nodeDocument) {
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
    const parent = queryOne(options?.root || getDefaultRoot());
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
    return queryAll(target, { displayed: true }).length > 0;
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
 * @param {FocusableOptions} [options]
 * @returns {boolean}
 */
export function isFocusable(target, options) {
    const nodes = queryAll(...arguments);
    return nodes.length && nodes.every((node) => isNodeFocusable(node, options));
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
    return queryAll(target, { viewPort: true }).length > 0;
}

/**
 * Returns whether an element is scrollable.
 *
 * @param {Target} target
 * @param {"x" | "y"} [axis]
 * @returns {boolean}
 */
export function isScrollable(target, axis) {
    const nodes = queryAll(target);
    return nodes.length && nodes.every((node) => isNodeScrollable(node, axis));
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
    return queryAll(target, { visible: true }).length > 0;
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
    return elementsMatch(queryAll(target), selector);
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
 * - `:iframe`: matches nodes that are `<iframe>` elements, and returns their `body`
 *  if it is ready;
 * - `:last`: matches the last node matching the selector (regardless of its actual
 *  DOM siblings);
 * - `:selected`: matches nodes that are selected (e.g. `<option>` elements);
 * - `:shadow`: matches nodes that have shadow roots, and returns their shadow root;
 * - `:scrollable`: matches nodes that are scrollable (see {@link isScrollable});
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
    if (!target) {
        return [];
    }
    if (target.raw) {
        return queryAll(String.raw(...arguments));
    }

    const { exact, displayed, root, viewPort, visible } = options || {};

    /** @type {Node[]} */
    let nodes = [];
    let selector;

    if (typeof target === "string") {
        nodes = root ? queryAll(root) : [getDefaultRoot()];
        selector = target.trim();
        // HTMLSelectElement is iterable ¯\_(ツ)_/¯
    } else if (isIterable(target) && !isNode(target)) {
        nodes = filterUniqueNodes(target);
    } else {
        nodes = filterUniqueNodes([target]);
    }

    if (selector && nodes.length) {
        if (rCustomPseudoClass.test(selector)) {
            nodes = queryWithCustomSelector(nodes, selector);
        } else {
            nodes = filterUniqueNodes(nodes.flatMap((node) => DESCENDANTS(node, selector)));
        }
    }

    /** @type {string} */
    let prefix, suffix;
    if (visible + displayed > 1) {
        throw new HootDomError(
            `cannot use more than one visibility modifier ('visible' implies 'displayed')`
        );
    }
    if (viewPort) {
        nodes = nodes.filter(isNodeInViewPort);
        suffix = "in viewport";
    } else if (visible) {
        nodes = nodes.filter(isNodeVisible);
        prefix = "visible";
    } else if (displayed) {
        nodes = nodes.filter(isNodeDisplayed);
        prefix = "displayed";
    }

    const count = nodes.length;
    if ($isInteger(exact) && count !== exact) {
        const s = count === 1 ? "" : "s";
        const strPrefix = prefix ? `${prefix} ` : "";
        const strSuffix = suffix ? ` ${suffix}` : "";
        const strSelector = typeof target === "string" ? `(selector: "${target}")` : "";
        throw new HootDomError(
            `found ${count} ${strPrefix}node${s}${strSuffix} instead of ${exact} ${strSelector}`
        );
    }

    return nodes;
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
    return getNodeAttribute(queryOne(target, options), attribute);
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
    return queryAll(target, options).map((node) => getNodeAttribute(node, attribute));
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
    return queryAll(target, options).map((node) => node[property]);
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
    return queryAll(...arguments).map(getNodeRect);
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
    return queryAll(...arguments).map((node) => getNodeText(node, options));
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
    return queryAll(...arguments).map(getNodeValue);
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
    return queryAll(...arguments)[0] || null;
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
    if (target.raw) {
        return queryOne(String.raw(...arguments));
    }
    if ($isInteger(options?.exact)) {
        throw new HootDomError(
            `cannot call \`queryOne\` with 'exact'=${options.exact}: did you mean to use \`queryAll\`?`
        );
    }
    return queryAll(target, { ...options, exact: 1 })[0];
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
    return getNodeRect(queryOne(...arguments), options);
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
    return getNodeText(queryOne(...arguments), options);
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
    return getNodeValue(queryOne(...arguments));
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
 * @returns {Deferred<Element>}
 * @example
 *  const button = await waitFor(`button`);
 *  button.click();
 */
export function waitFor(target, options) {
    return waitUntil(() => queryFirst(...arguments), {
        message: `Could not find elements matching "${target}" within %timeout% milliseconds`,
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
    let count = 0;
    return waitUntil(
        () => {
            count = queryAll(...arguments).length;
            return !count;
        },
        {
            message: () =>
                `Could still find ${count} elements matching "${target}" after %timeout% milliseconds`,
            ...options,
        }
    );
}
