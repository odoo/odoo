/** @odoo-module */

import { HootDomError, getTag, isFirefox, isIterable, parseRegExp } from "../hoot_dom_utils";

/**
 * @typedef {{
 *  w?: number;
 *  h?: number;
 *  width?: number;
 *  height?: number;
 * }} Dimensions
 *
 * @typedef {(node: Node, selector: string) => Node[]} NodeGetter
 *
 * @typedef {string | string[] | number | boolean | File[]} NodeValue
 *
 * @typedef {{
 *  x?: number;
 *  y?: number;
 *  left?: number;
 *  top?: number,
 *  clientX?: number;
 *  clientY?: number;
 *  pageX?: number;
 *  pageY?: number;
 * }} Position
 *
 * @typedef {(content: string) => (node: Node, index: number, nodes: Node[]) => boolean | Node} PseudoClassPredicateBuilder
 *
 * @typedef {{
 *  displayed?: boolean;
 *  exact?: number;
 *  root?: HTMLElement;
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
 * @typedef {MaybeIterable<Node> | string | null | undefined | false} Target
 *
 * @typedef {{
 *  message?: string | () => string;
 *  timeout?: number;
 * }} WaitOptions
 */

/**
 * @template T
 * @typedef {T | Iterable<T>} MaybeIterable
 */

//-----------------------------------------------------------------------------
// Global
//-----------------------------------------------------------------------------

const {
    Boolean,
    cancelAnimationFrame,
    clearTimeout,
    console: { warn: $warn },
    document,
    Map,
    Math: { floor: $floor },
    MutationObserver,
    Number: { isInteger: $isInteger, isNaN: $isNaN, parseInt: $parseInt, parseFloat: $parseFloat },
    Object: { keys: $keys, values: $values },
    Promise,
    Reflect: { ownKeys: $ownKeys },
    RegExp,
    requestAnimationFrame,
    Set,
    setTimeout,
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
 * @param {Iterable<Node>} nodesToFilter
 */
const filterUniqueNodes = (nodesToFilter) => {
    /** @type {Node[]} */
    const nodes = [];
    for (const node of nodesToFilter) {
        if (isNode(node) && !nodes.includes(node)) {
            nodes.push(node);
        }
    }
    return nodes;
};

/**
 * @param {string} string
 */
const getStringContent = (string) => {
    return string.match(R_QUOTE_CONTENT)?.[2] || string;
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
const isNodeCssVisible = (node) => {
    const element = ensureElement(node);
    if (element === getDefaultRoot() || isRootElement(element)) {
        return true;
    }
    const style = getStyle(element);
    if (style?.visibility === "hidden" || style?.opacity === "0") {
        return false;
    }
    const parent = element.parentNode;
    return !parent || isNodeCssVisible(parent);
};

/**
 * @param {Window | Node} node
 */
const isNodeDisplayed = (node) => {
    const element = ensureElement(node);
    if (!isInDOM(element)) {
        return false;
    }
    if (isRootElement(element) || element.offsetParent || element.closest("svg")) {
        return true;
    }
    // `position=fixed` elements in Chrome do not have an `offsetParent`
    return !isFirefox() && getStyle(element)?.position === "fixed";
};

/**
 * @param {Window | Node} node
 * @param {"x" | "y"} axis
 */
const isNodeScrollable = (node, axis) => {
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
};

/**
 * @param {Window | Node} node
 */
const isNodeVisible = (node) => {
    const element = ensureElement(node);

    // Must be displayed and not hidden by CSS
    if (!isNodeDisplayed(element) || !isNodeCssVisible(element)) {
        return false;
    }

    let visible = false;

    // Check size (width & height)
    if (typeof element.getBoundingClientRect === "function") {
        const { width, height } = getNodeRect(element);
        visible = width > 0 && height > 0;
    }

    // Check content (if display=contents)
    if (!visible && getStyle(element)?.display === "contents") {
        for (const child of element.childNodes) {
            if (isNodeVisible(child)) {
                return true;
            }
        }
    }

    return visible;
};

/**
 * @param {Element} [el]
 */
const isRootElement = (el) => el && R_ROOT_ELEMENT.test(el.nodeName || "");

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

// Following selector is based on this spec:
// https://html.spec.whatwg.org/multipage/interaction.html#dom-tabindex
const FOCUSABLE_SELECTOR = [
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
]
    .map((sel) => `${sel}:not([tabindex="-1"])`)
    .join(",");

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
    width: null,
    height: null,
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
            if (getTag(node) !== "iframe") {
                const iframeNode = node.querySelector("iframe");
                if (iframeNode) {
                    node = iframeNode;
                } else {
                    return false;
                }
            }
            const doc = node.contentDocument;
            return doc?.readyState !== "loading" ? doc : false;
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
    .set("text", makePatternBasedPseudoClass("text", getNodeText))
    .set("value", makePatternBasedPseudoClass("value", getNodeValue))
    .set("visible", () => {
        return function visible(node) {
            return isNodeVisible(node);
        };
    });

let rCustomPseudoClass = compilePseudoClassRegex();

//-----------------------------------------------------------------------------
// Exports
//-----------------------------------------------------------------------------

export function cleanupDOM() {
    // Dimensions
    currentDimensions.width = null;
    currentDimensions.height = null;

    // Observers
    const remainingObservers = observers.size;
    if (remainingObservers) {
        $warn(`${remainingObservers} observers still running`);
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

/**
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
 * Returns the list of focusable elements in the given parent, sorted by their `tabIndex`
 * property.
 *
 * @see {@link isFocusable} for more information
 * @param {Document | DocumentFragment | Element} [parent] default: current fixture
 * @returns {Element[]}
 * @example
 *  getFocusableElements();
 */
export function getFocusableElements(parent) {
    parent ||= getDefaultRoot();
    if (typeof parent.querySelectorAll !== "function") {
        return [];
    }
    const byTabIndex = {};
    for (const element of parent.querySelectorAll(FOCUSABLE_SELECTOR)) {
        if (isNodeDisplayed(element)) {
            const tabindex = element.tabIndex;
            if (!byTabIndex[tabindex]) {
                byTabIndex[tabindex] = [];
            }
            byTabIndex[tabindex].push(element);
        }
    }
    const withTabIndexZero = byTabIndex[0] || [];
    delete byTabIndex[0];
    return [...$values(byTabIndex).flat(), ...withTabIndexZero];
}

/**
 * @param {Dimensions} dimensions
 * @returns {number}
 */
export function getHeight(dimensions) {
    if (dimensions) {
        for (const prop of ["h", "height"]) {
            const value = $parseFloat(dimensions[prop]);
            if (!$isNaN(value)) {
                return value;
            }
        }
    }
    return NaN;
}

/**
 * Returns the next focusable element after the current active element if it is
 * contained in the given parent.
 *
 * @see {@link getFocusableElements}
 * @param {Document | DocumentFragment | Element} [parent] default: current fixture
 * @returns {Element | null}
 * @example
 *  getPreviousFocusableElement();
 */
export function getNextFocusableElement(parent) {
    parent ||= getDefaultRoot();
    const focusableEls = getFocusableElements(parent);
    const index = focusableEls.indexOf(getActiveElement(parent));
    return focusableEls[index + 1] || null;
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
 * @param {Document | DocumentFragment | Element} [parent] default: current fixture
 * @returns {Element | null}
 * @example
 *  getPreviousFocusableElement();
 */
export function getPreviousFocusableElement(parent) {
    parent ||= getDefaultRoot();
    const focusableEls = getFocusableElements(parent);
    const index = focusableEls.indexOf(getActiveElement(parent));
    return index < 0 ? focusableEls.at(-1) : focusableEls[index - 1] || null;
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
 * @param {Dimensions} dimensions
 * @returns {number}
 */
export function getWidth(dimensions) {
    if (dimensions) {
        for (const prop of ["w", "width"]) {
            const value = $parseFloat(dimensions[prop]);
            if (!$isNaN(value)) {
                return value;
            }
        }
    }
    return NaN;
}

/**
 * @param {Node} [node]
 * @returns {Window}
 */
export function getWindow(node) {
    return getDocument(node).defaultView;
}

/**
 * @param {Position} position
 * @returns {number}
 */
export function getX(position) {
    if (position) {
        for (const prop of ["x", "left", "clientX", "pageX", "screenX"]) {
            const value = $parseFloat(position[prop]);
            if (!$isNaN(value)) {
                return value;
            }
        }
    }
    return NaN;
}

/**
 * @param {Position} position
 * @returns {number}
 */
export function getY(position) {
    if (position) {
        for (const prop of ["y", "top", "clientY", "pageY", "screenY"]) {
            const value = $parseFloat(position[prop]);
            if (!$isNaN(value)) {
                return value;
            }
        }
    }
    return NaN;
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
 * Note: this does NOT support elements with `contenteditable="true"`.
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
 * Returns whether the given target is an {@link EventTarget}.
 *
 * @template T
 * @param {T} target
 * @returns {T extends EventTarget ? true : false}
 * @example
 *  isEventTarget(window); // true
 * @example
 *  isEventTarget(new App()); // false
 */
export function isEventTarget(target) {
    return target && typeof target.addEventListener === "function";
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
    const nodes = queryAll(target);
    return nodes.length && nodes.every(isNodeFocusable);
}

/**
 * Returns whether the given target is contained in the current root document.
 *
 * @param {Window | Node} target
 * @returns {boolean}
 * @example
 *  isInDOM(document.querySelector("div")); // true
 * @example
 *  isInDOM(document.createElement("div")); // false
 */
export function isInDOM(target) {
    target = ensureElement(target);
    if (!target) {
        return false;
    }
    const frame = getParentFrame(target);
    if (frame) {
        return isInDOM(frame);
    }
    while (target) {
        if (target === document) {
            return true;
        }
        target = target.parentNode;
        if (target?.host) {
            target = target.host.parentNode;
        }
    }
    return false;
}

/**
 * Returns whether the given object is a {@link Node} object.
 *
 * @template T
 * @param {T} object
 * @returns {T extends Node ? true : false}
 */
export function isNode(object) {
    return typeof object === "object" && Boolean(object?.nodeType);
}

/**
 * @param {Node} node
 */
export function isNodeFocusable(node) {
    return isNodeDisplayed(node) && node.matches?.(FOCUSABLE_SELECTOR);
}

/**
 * Checks whether an target is visible, meaning that it is "displayed" (see {@link isDisplayed}),
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
 * @param {MaybeIterable<Node>} node
 * @param {string} selector
 * @returns {boolean}
 */
export function matches(node, selector) {
    const nodes = isIterable(node) && !isNode(node) ? [...node] : [node];
    if (!nodes.length) {
        return false;
    }

    return parseSelector(selector).some((selectorParts) => {
        const [baseSelector, ...filters] = selectorParts.at(-1);
        for (let i = 0; i < nodes.length; i++) {
            if (baseSelector && !nodes[i].matches(baseSelector)) {
                return false;
            }
            if (!filters.every((filter) => matchFilter(filter, nodes, i))) {
                return false;
            }
        }
        return true;
    });
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
 * @param {Dimensions} dimensions
 * @returns {[number, number]}
 */
export function parseDimensions(dimensions) {
    return [getWidth(dimensions), getHeight(dimensions)];
}

/**
 * @param {Position} position
 * @returns {[number, number]}
 */
export function parsePosition(position) {
    return [getX(position), getY(position)];
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
 * - `visible`: whether the nodes must be "visible" (see {@link isVisible}).
 *      * This option implies `displayed`
 *
 * [1] these filters (except for `exact` and `root`) achieve the same result as
 *  using their homonym pseudo-classes on the final group of the given selector
 *  string (e.g. ```queryAll`ul > li:visible`;``` = ```queryAll("ul > li", { visible: true })```).
 *
 * @param {Target} target
 * @param {QueryOptions} [options]
 * @returns {Node[]}
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

    const { exact, displayed, root, visible } = options || {};

    /** @type {Node[]} */
    let nodes = [];
    let selector;

    if (typeof target === "string") {
        nodes = filterUniqueNodes([root || getDefaultRoot()]);
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

    /** @type {string[]} */
    const prefixes = [];
    if (visible) {
        nodes = nodes.filter(isNodeVisible);
        prefixes.push("visible");
    }
    if (displayed) {
        if (visible) {
            throw new HootDomError(
                `cannot use both 'visible' and 'displayed' ('visible' always implies 'displayed')`
            );
        }
        nodes = nodes.filter(isNodeDisplayed);
        prefixes.push("displayed");
    }

    const count = nodes.length;
    if ($isInteger(exact) && count !== exact) {
        const s = count === 1 ? "" : "s";
        const strPrefix = prefixes.length ? ` ${and(prefixes)}` : "";
        const strSelector = typeof target === "string" ? `(selector: "${target}")` : "";
        throw new HootDomError(
            `found ${count}${strPrefix} node${s} instead of ${exact} ${strSelector}`
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
    return queryAll(target, options).map(getNodeRect);
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
    return queryAll(target, options).map((node) => getNodeText(node, options));
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
    return queryAll(target, options).map(getNodeValue);
}

/**
 * Performs a {@link queryAll} with the given arguments and returns the first result
 * or `null`.
 *
 * @param {Target} target
 * @param {QueryOptions} options
 * @returns {Node | null}
 */
export function queryFirst(target, options) {
    return queryAll(target, options)[0] || null;
}

/**
 * Performs a {@link queryAll} with the given arguments and returns the last result
 * or `null`.
 *
 * @param {Target} target
 * @param {QueryOptions} options
 * @returns {Node | null}
 */
export function queryLast(target, options) {
    return queryAll(target, options).at(-1) || null;
}

/**
 * Performs a {@link queryAll} with the given arguments, along with a forced `exact: 1`
 * option to ensure only one node matches the given {@link Target}.
 *
 * The returned value is a single node instead of a list of nodes.
 *
 * @param {Target} target
 * @param {Omit<QueryOptions, "exact">} [options]
 * @returns {Node}
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
    return queryAll(target, { exact: 1, ...options })[0];
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
    return getNodeRect(queryOne(target, options), options);
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
    return getNodeText(queryOne(target, options), options);
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
    return getNodeValue(queryOne(target, options));
}

/**
 * @param {string} pseudoClass
 * @param {PseudoClassPredicateBuilder} predicate
 */
export function registerPseudoClass(pseudoClass, predicate) {
    if (customPseudoClasses.has(pseudoClass)) {
        throw new HootDomError(`cannot register pseudo-class: '${pseudoClass}' already exists`);
    }
    customPseudoClasses.set(pseudoClass, predicate);
    rCustomPseudoClass = compilePseudoClassRegex();
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

/**
 * Combination of {@link queryAll} and {@link waitUntil}: waits for a given target
 * to match elements in the DOM and returns the first matching node when it appears
 * (or immediatlly if it is already present).
 *
 * @see {@link queryAll}
 * @see {@link waitUntil}
 * @param {Target} target
 * @param {QueryOptions & WaitOptions} [options]
 * @returns {Promise<Node>}
 * @example
 *  const button = await waitFor(`button`);
 *  button.click();
 */
export function waitFor(target, options) {
    return waitUntil(() => queryFirst(target, options), {
        message: `Could not find elements matching "${target}" within %timeout% milliseconds`,
        ...options,
    });
}

/**
 * Opposite of {@link waitFor}: waits for a given target to disappear from the DOM.
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
            count = queryAll(target, options).length;
            return !count;
        },
        {
            message: () =>
                `Could still find ${count} elements matching "${target}" after %timeout% milliseconds`,
            ...options,
        }
    );
}

/**
 * Returns a promise fulfilled when the given `predicate` returns a truthy value,
 * with the value of the promise being the return value of the `predicate`.
 *
 * The `predicate` is run once initially and then each time the DOM is mutated (see
 * {@link observe} for more information).
 *
 * The promise automatically rejects after a given `timeout` (defaults to 5 seconds).
 *
 * @template T
 * @param {() => T} predicate
 * @param {WaitOptions} [options]
 * @returns {Promise<T>}
 * @example
 *  await waitUntil(() => []); // -> []
 * @example
 *  const button = await waitUntil(() => document.querySelector("button"));
 *  button.click();
 */
export async function waitUntil(predicate, options) {
    const result = predicate();
    if (result) {
        return result;
    }

    let disconnect;
    let handle;
    let timeoutId;
    return new Promise((resolve, reject) => {
        const runCheck = () => {
            if (handle) {
                cancelAnimationFrame(handle);
            }
            const result = predicate();
            if (result) {
                resolve(result);
            } else {
                handle = requestAnimationFrame(runCheck);
            }
        };

        const timeout = $floor(options?.timeout ?? 200);
        timeoutId = setTimeout(() => {
            let message = options?.message || `'waitUntil' timed out after %timeout% milliseconds`;
            if (typeof message === "function") {
                message = message();
            }
            reject(new HootDomError(message.replace("%timeout%", String(timeout))));
        }, timeout);

        disconnect = observe(getDefaultRoot(), runCheck);
        runCheck();
    }).finally(() => {
        if (disconnect) {
            disconnect();
        }
        if (handle) {
            cancelAnimationFrame(handle);
        }
        if (timeoutId) {
            clearTimeout(timeoutId);
        }
    });
}

/**
 * Returns a function checking that the given target does not contain any unexpected
 * key. The list of accepted keys is the initial list of keys of the target, along
 * with an optional `whiteList` argument.
 *
 * @template T
 * @param {T} target
 * @param {string[]} [whiteList]
 * @returns {(cleanup: boolean) => void}
 * @example
 *  afterEach(watchKeys(window, ["odoo"]));
 */
export function watchKeys(target, whiteList) {
    const acceptedKeys = new Set([...$ownKeys(target), ...(whiteList || [])]);

    /**
     * @param {boolean} [cleanup=true]
     */
    return function checkKeys(cleanup = true) {
        if (!isInDOM(target)) {
            return;
        }
        const keysDiff = $ownKeys(target).filter(
            (key) => $isNaN($parseFloat(key)) && !acceptedKeys.has(key)
        );
        if (keysDiff.length) {
            if (cleanup) {
                for (const key of keysDiff) {
                    delete target[key];
                }
            } else {
                $warn(
                    `${target.constructor.name} has`,
                    keysDiff.length,
                    `unexpected keys:`,
                    keysDiff
                );
            }
        }
    };
}
