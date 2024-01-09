/** @odoo-module */

import { HootDomError, getTag, isIterable, parseRegExp } from "../hoot_dom_utils";

/**
 * @typedef {{
 *  w?: number;
 *  h?: number;
 *  width?: number;
 *  height?: number;
 * }} Dimensions
 *
 * @typedef {{
 *  size?: Dimensions;
 * }} FixtureOptions
 *
 * @typedef {(node: Node, selector: string) => Node[]} NodeGetter
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
 * @typedef {(content: string) => (node: Node, index: number, nodes: Node[]) => boolean | Node} PseudoSelectorPredicateBuilder
 *
 * @typedef {{
 *  displayed?: boolean;
 *  exact?: number;
 *  root?: HTMLElement;
 *  visible?: boolean;
 * }} QueryOptions
 *
 * @typedef {MaybeIterable<Node> | string | null | undefined | false} Target
 *
 * @typedef {{
 *  message?: string;
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
    clearTimeout,
    console,
    document,
    Map,
    matchMedia,
    Math,
    MutationObserver,
    Number,
    Object,
    Promise,
    Reflect,
    RegExp,
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

const compilePseudoSelectorRegex = () =>
    new RegExp(`:(${[...customPseudoSelectors.keys()].join("|")})`);

/**
 * @param {string} selector
 */
const extractPseudoSelectorFilters = (selector) => {
    const addCurrentFilter = () => {
        const [pseudo, content] = currentPseudo;
        currentPseudo = null;
        const makeFilter = customPseudoSelectors.get(pseudo);
        filters.push(Object.assign(makeFilter(trimQuotes(content)), { _pseudo: pseudo }));
    };

    selector ||= "";

    let baseSelector = "";
    let closedParens = 0;
    let currentQuote = null;
    let currentPseudo = null;
    let openParens = 0;

    /** @type {(ReturnType<PseudoSelectorPredicateBuilder> & { _pseudo: string })[]} */
    const filters = [];
    for (let i = 0; i < selector.length; i++) {
        if (currentPseudo) {
            if (currentQuote) {
                // In quotes
                if (selector[i] === currentQuote) {
                    // Close quotes
                    currentQuote = null;
                }
            } else if (QUOTE_REGEX.test(selector[i])) {
                // Open quotes
                currentQuote = selector[i];
            }
        }

        if (!currentQuote) {
            if (!currentPseudo && selector[i] === ":") {
                let pseudo = "";
                while (selector[i + 1] && PSEUDO_SELECTOR_CHAR_REGEX.test(selector[i + 1])) {
                    pseudo += selector[++i];
                }

                if (customPseudoSelectors.has(pseudo)) {
                    // Open pseudo selector block
                    currentPseudo = [pseudo, ""];

                    if (selector[i + 1] === "(") {
                        openParens++;
                        i++;
                    } else {
                        // No parentheses => add filter
                        addCurrentFilter();
                    }
                    continue;
                } else {
                    // Native pseudo selector => left as is
                    baseSelector += `:${pseudo}`;
                    continue;
                }
            }

            if (selector[i] === "(") {
                // Open parentheses
                openParens++;
            } else if (selector[i] === ")") {
                // Close parentheses
                closedParens++;

                if (currentPseudo && closedParens === openParens) {
                    // Close pseudo selector block
                    addCurrentFilter();
                    continue;
                }
            }
        }

        // Append char to current pseudo selector
        if (currentPseudo) {
            currentPseudo[1] += selector[i];
        } else {
            baseSelector += selector[i];
        }
    }

    if (currentPseudo) {
        addCurrentFilter();
    }

    return { baseSelector, filters };
};

/**
 * @param {...Node} nodesToFilter
 */
const filterNodes = (...nodesToFilter) => {
    /** @type {Node[]} */
    const nodes = [];
    for (let node of nodesToFilter) {
        if (isDocument(node)) {
            node = node.documentElement;
        }
        if (isNode(node) && !nodes.includes(node)) {
            nodes.push(node);
        }
    }
    return nodes;
};

/**
 * @param {Node} node
 * @returns {ReturnType<typeof getNodeValue> & ReturnType<typeof getNodeText>}
 */
const getNodeContent = (node) => {
    switch (getTag(node)) {
        case "input":
        case "option":
        case "textarea":
            return getNodeValue(node);
        case "select":
            return [...node.selectedOptions].map(getNodeContent).join(",");
    }
    return getNodeText(node);
};

/**
 * @param {string} string
 */
const hasUnclosedScope = (string) => {
    for (const [start, end] of SCOPE_DELIMITERS) {
        if ((string.match(start) || []).length > (string.match(end) || []).length) {
            return true;
        }
    }
    return false;
};

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
    const style = getStyle(node);
    if (style?.visibility === "hidden" || style?.opacity === "0") {
        return false;
    }
    const parent = node.parentNode;
    return (
        !parent ||
        parent === getDefaultRoot() ||
        parent === getDocument(node).body ||
        isNodeCssVisible(parent)
    );
};

/**
 * @param {Window | Node} node
 */
const isNodeDisplayed = (node) => {
    if (isWindow(node) || isDocument(node)) {
        return true;
    } else if (!isInDOM(node)) {
        return false;
    }
    let visible = false;
    if ("offsetWidth" in node && "offsetHeight" in node) {
        visible = node.offsetWidth > 0 && node.offsetHeight > 0;
    } else if (typeof node.getBoundingClientRect === "function") {
        const { width, height } = getRect(node);
        visible = width > 0 && height > 0;
    }
    if (!visible && getStyle(node)?.display === "contents") {
        for (const child of node.childNodes) {
            if (isNodeDisplayed(child)) {
                return true;
            }
        }
    }
    return visible;
};

/**
 * @param {Node} node
 */
const isNodeFocusable = (node) => isNodeDisplayed(node) && node.matches?.(FOCUSABLE_SELECTOR);

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
const isNodeVisible = (node) => isNodeDisplayed(node) && isNodeCssVisible(node);

/**
 * @template T
 * @param {T} object
 * @returns {T extends Window ? true : false}
 */
const isWindow = (object) => typeof object === "object" && object?.window === object;

/**
 * @param {string} query
 * @param {number} width
 * @param {number} height
 */
const matchesQuery = (query, width, height) =>
    query
        .replace(/\s+/g, "")
        .split(",")
        .some((orPart) =>
            orPart.split("and").every((andPart) => matchesQueryPart(andPart, width, height))
        );

/**
 * @param {string} query
 * @param {number} width
 * @param {number} height
 */
const matchesQueryPart = (query, width, height) => {
    const minWidth = query.match(/min-width:\s*(\d+)/)?.[1];
    const maxWidth = query.match(/max-width:\s*(\d+)/)?.[1];
    const minHeight = query.match(/min-height:\s*(\d+)/)?.[1];
    const maxHeight = query.match(/max-height:\s*(\d+)/)?.[1];
    const result =
        (!minWidth || width >= parseInt(minWidth)) &&
        (!maxWidth || width <= parseInt(maxWidth)) &&
        (!minHeight || height >= parseInt(minHeight)) &&
        (!maxHeight || height <= parseInt(maxHeight));
    return query.includes("not") ? !result : result;
};

/**
 * Converts a CSS pixel value to a number, removing the 'px' part.
 *
 * @param {string} val
 */
const pixelValueToNumber = (val) => Number(val.endsWith("px") ? val.slice(0, -2) : val);

/**
 * @param {Node[]} nodes
 * @param {string} selector
 */
const queryWithCustomSelector = (nodes, selector) => {
    // Separate selector groups
    const foundNodes = [];
    for (const selectorGroup of selector.split(/\s*,\s*/g)) {
        // Separate selector parts
        const selectorParts = selectorGroup
            .replace(/([+>~])\s*(\S)/g, " $1$2") // Removes space between combinators and next char
            .split(/\s+/g);

        let groupNodes = nodes;
        for (let i = 0; i < selectorParts.length; i++) {
            let selectorPart = selectorParts[i];
            let nodeGetter;
            switch (selectorPart[0]) {
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
                selectorPart = selectorPart.slice(1);
            }

            // Appends next groups until the scope is closed
            while (hasUnclosedScope(selectorPart) && i < selectorParts.length - 1) {
                selectorPart += ` ${selectorParts[++i]}`;
            }

            // Generate base selectors and isolate pseudo-selector filters
            const { baseSelector, filters } = extractPseudoSelectorFilters(selectorPart);

            // Retrieve matching nodes and apply filters
            const getNodes = nodeGetter || DESCENDANTS;
            const nextNodes = [];
            for (const node of groupNodes) {
                // Get nodes (direct children, descendants, next siblings, etc.)
                const targetNodes = getNodes(node, baseSelector);

                if (!filters.length) {
                    // No filters => all nodes are valid
                    nextNodes.push(...targetNodes);
                    continue;
                }

                // Filter/replace nodes based on custom pseudo-selectors
                for (let i = 0; i < targetNodes.length; i++) {
                    const pseudoReturningNode = [];
                    let returnNode = targetNodes[i];

                    for (const filter of filters) {
                        const result = filter(returnNode, i, targetNodes);
                        if (result === false) {
                            returnNode = null;
                            break;
                        } else if (result === true) {
                            continue;
                        }

                        returnNode = result;
                        pseudoReturningNode.push(filter._pseudo);
                    }

                    if (pseudoReturningNode.length > 1) {
                        throw selectorError(
                            pseudoReturningNode[0],
                            `cannot use multiple pseudo selectors returning nodes (${and(
                                pseudoReturningNode
                            )})`
                        );
                    }

                    if (returnNode) {
                        nextNodes.push(returnNode);
                    }
                }
            }

            groupNodes = filterNodes(...nextNodes);
        }

        foundNodes.push(...groupNodes);
    }

    return foundNodes;
};

/**
 * @param {string} pseudoSelector
 * @param {string} message
 */
const selectorError = (pseudoSelector, message) =>
    new HootDomError(`invalid selector \`:${pseudoSelector}\`: ${message}`);

/**
 * @param {string} string
 */
const trimQuotes = (string) => string.match(/^\s*(['"`])?(.*?)\1?\s*$/)?.[2] || string;

// Regexes
const QUOTE_REGEX = /['"`]/;
const PSEUDO_SELECTOR_CHAR_REGEX = /[\w-]/;
const SCOPE_DELIMITERS = [
    [/\[/g, /]/g],
    [/\(/g, /\)/g],
];

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
const DESCENDANTS = (node, selector) => [
    ...(node.querySelectorAll?.(`:scope ${selector || "*"}`) || []),
];

/** @type {NodeGetter} */
const NEXT_SIBLING = (node, selector) => {
    const sibling = node.nextSibling;
    return sibling?.matches?.(selector) ? [sibling] : [];
};

/** @type {NodeGetter} */
const NEXT_SIBLINGS = (node, selector) => {
    const siblings = [];
    while ((node = node.nextSibling)) {
        if (node.matches?.(selector)) {
            siblings.push(node);
        }
    }
    return siblings;
};

/** @type {Map<HTMLElement, { callbacks: Set<MutationCallback>, observer: MutationObserver }>} */
const observers = new Map();
let currentDimensions = {
    width: null,
    height: null,
};
let getDefaultRoot = () => document.documentElement;

//-----------------------------------------------------------------------------
// Pseudo selectors
//-----------------------------------------------------------------------------

/** @type {Map<string, PseudoSelectorPredicateBuilder>} */
const customPseudoSelectors = new Map();

customPseudoSelectors
    .set("contains", (content) => {
        let regex;
        try {
            regex = parseRegExp(content);
        } catch (err) {
            throw selectorError("contains", err.message);
        }
        if (regex instanceof RegExp) {
            return (node) => regex.test(String(getNodeContent(node)));
        } else {
            const lowerContent = content.toLowerCase();
            return (node) => String(getNodeContent(node)).toLowerCase().includes(lowerContent);
        }
    })
    .set("displayed", () => {
        return (node) => isNodeDisplayed(node);
    })
    .set("empty", () => {
        return (node) => isEmpty(node);
    })
    .set("eq", (content) => {
        const index = Number(content);
        if (!Number.isInteger(index)) {
            throw selectorError("eq", `expected index to be an integer (got ${content})`);
        }
        return (node, i) => i === index;
    })
    .set("first", () => {
        return (node, i) => i === 0;
    })
    .set("focusable", () => {
        return (node) => isNodeFocusable(node);
    })
    .set("has", (content) => {
        return (node) => Boolean(queryAll(content, { root: node }).length);
    })
    .set("hidden", () => {
        return (node) => !isNodeVisible(node);
    })
    .set("iframe", () => {
        return (node) => {
            if (getTag(node) !== "iframe") {
                const iframeNode = node.querySelector("iframe");
                if (iframeNode) {
                    node = iframeNode;
                } else {
                    return false;
                }
            }
            const document = node.contentDocument;
            return document && document.readyState !== "loading" ? document.documentElement : false;
        };
    })
    .set("last", () => {
        return (node, i, nodes) => i === nodes.length - 1;
    })
    .set("not", (content) => {
        return (node) => !matches(node, content);
    })
    .set("scrollable", () => {
        return (node) => isNodeScrollable(node);
    })
    .set("selected", () => {
        return (node) => Boolean(node.selected);
    })
    .set("shadow", () => {
        return (node) => node.shadowRoot || false;
    })
    .set("visible", () => {
        return (node) => isNodeVisible(node);
    });

let customPseudoSelectorRegex = compilePseudoSelectorRegex();

//-----------------------------------------------------------------------------
// Exports
//-----------------------------------------------------------------------------

export function cleanupObservers() {
    const remainingObservers = observers.size;
    if (remainingObservers) {
        console.warn(`${remainingObservers} observers still running`);
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
        getDefaultRoot = () => document.documentElement;
    }
}

/**
 * @param {Node} [node]
 */
export function getActiveElement(node) {
    return getDocument(node).activeElement;
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
    return [...Object.values(byTabIndex).flat(), ...withTabIndexZero];
}

/**
 * @param {Dimensions} dimensions
 * @returns {number}
 */
export function getHeight(dimensions) {
    if (dimensions) {
        for (const prop of ["h", "height"]) {
            const value = parseInt(dimensions[prop]);
            if (typeof value === "number") {
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
 * @returns {string | string[] | number | boolean | File[]}
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
    return node.value.trim();
}

/**
 * @param {Node} node
 * @returns {string}
 */
export function getNodeText(node) {
    if (typeof node.innerText === "string") {
        return node.innerText.trim();
    } else {
        return node.textContent.trim();
    }
}

/**
 * Returns the parent `<iframe>` of a given node (if any).
 *
 * @param {Node} node
 * @returns {HTMLIFrameElement | null}
 */
export function getParentFrame(node) {
    const view = node.ownerDocument.defaultView;
    if (view !== view.parent) {
        const currentDocument = node.ownerDocument;
        for (const iframe of view.parent.document.getElementsByTagName("iframe")) {
            if (iframe.contentDocument === currentDocument) {
                return iframe;
            }
        }
    }
    return null;
}

/**
 * Returns the previous focusable element after the current active element if it is
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
 * Returns the bounding {@link DOMRect} of a given node (or an empty one if none is given).
 * This helper is a bit different than the native {@link Element.getBoundingClientRect}:
 * - rects take their positions relative to the top window element (instead of their
 *  parent `<iframe>` if any);
 * - they can be trimmed to remove padding with the `trimPadding` option.
 *
 * @param {Node} node
 * @param {{ trimPadding?: boolean }} [options]
 * @returns {DOMRect}
 */
export function getRect(node, options) {
    if (!isElement(node)) {
        return new DOMRect();
    }

    const rect = node.getBoundingClientRect();
    const parentFrame = getParentFrame(node);
    if (parentFrame) {
        const parentRect = getRect(parentFrame);
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
            const value = parseInt(dimensions[prop]);
            if (typeof value === "number") {
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
        for (const prop of ["x", "left", "clientX", "pageX"]) {
            const value = parseInt(position[prop]);
            if (typeof value === "number") {
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
        for (const prop of ["y", "top", "clientY", "pageY"]) {
            const value = parseInt(position[prop]);
            if (typeof value === "number") {
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
 * Checks whether a target is displayed, meaning that it has a bounding box and
 * is contained in the current document.
 *
 * Note that it does not mean that the target is "visible" (it can still be hidden
 * by CSS properties such as `opacity` or `visiblity`).
 *
 * @param {Target} target
 * @returns {boolean}
 */
export function isDisplayed(target) {
    return Boolean(queryAll(target, { displayed: true }));
}

/**
 * Returns whether the given node is editable, meaning that it is an {@link Element}
 * that is either:
 * - an `":enabled"` `<input>` or `<textarea>` element;
 * - an element with the `contenteditable` property set to "true".
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
        (["input", "textarea"].includes(getTag(node)) || node.contentEditable === "true")
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
            return isEmpty(getNodeContent(node));
        }
        if (!isIterable(value)) {
            value = Object.keys(value);
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
    if (!target) {
        return false;
    }
    if (isWindow(target) || isDocument(target)) {
        return true;
    }
    const frame = getParentFrame(target);
    return frame ? isInDOM(frame) : document.contains(target);
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
 * Checks whether an target is visible, meaning that it is "displayed" (see {@link isDisplayed})
 * and is not hidden by CSS properties.
 *
 * Note that it does not take into account the target's position in the viewport
 * nor its color (for example, a text can be hidden by a same-colored background).
 *
 * @param {Target} target
 * @returns {boolean}
 */
export function isVisible(target) {
    const nodes = queryAll(target);
    return nodes.length && nodes.every(isNodeVisible);
}

/**
 * @param {MaybeIterable<Node>} node
 * @param {string} selector
 * @returns {boolean}
 */
export function matches(node, selector) {
    const nodes = isIterable(node) && !isNode(node) ? [...node] : [node];
    const { baseSelector, filters } = extractPseudoSelectorFilters(selector);
    for (let i = 0; i < nodes.length; i++) {
        const node = nodes[i];
        if (baseSelector && !node.matches(baseSelector)) {
            return false;
        }
        if (!filters.every((filter) => filter(node, i, nodes))) {
            return false;
        }
    }
    return true;
}

/**
 * @type {typeof matchMedia}
 */
export function mockedMatchMedia(query) {
    let onchange = null;
    return {
        addEventListener: (type, callback) => window.addEventListener("resize", callback),
        get matches() {
            let { width, height } = currentDimensions;
            width ||= window.innerWidth;
            height ||= window.innerHeight;
            return matchesQuery(query, width, height);
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
 * along with some additional custom pseudo-classes[1]:
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
 * An `options` object can be specified to filter[2] the results:
 * - `displayed`: whether the nodes must be "displayed" (see {@link isDisplayed});
 * - `exact`: the exact number of nodes to match (throws an error if the number of
 *  nodes doesn't match);
 * - `focusable`: whether the nodes must be "focusable" (see {@link isFocusable});
 * - `root`: the root node to query the selector in (defaults to the current fixture);
 * - `visible`: whether the nodes must be "visible" (see {@link isVisible}).
 *      * This option implies `displayed`
 *
 * [1] combinations of nested standard pseudo-selectors with custom pseudo-classes
 *  are not supported (e.g. `:not(:empty)`, `:has(:contains(foo))`, etc.).
 *
 * [2] these filters (except for `exact` and `root`) achieve the same result as
 *  using their homonym pseudo-selectors on the final group of the given selector
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
        nodes = filterNodes(root || getDefaultRoot());
        selector = target.trim();
        // HTMLSelectElement is iterable ¯\_(ツ)_/¯
    } else if (isIterable(target) && !isNode(target)) {
        nodes = filterNodes(...target);
    } else {
        nodes = filterNodes(target);
    }

    if (selector && nodes.length) {
        if (customPseudoSelectorRegex.test(selector)) {
            nodes = queryWithCustomSelector(nodes, selector);
        } else {
            nodes = filterNodes(...nodes.flatMap((node) => DESCENDANTS(node, selector)));
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
    if (Number.isInteger(exact) && count !== exact) {
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
 * Performs a {@link queryAll} with the given arguments and returns matching nodes'
 * *contents* (**value** or **inner text**).
 *
 * @param {Target} target
 * @param {QueryOptions} [options]
 * @returns {string[]}
 */
export function queryAllContents(target, options) {
    return queryAll(target, options).map(getNodeContent);
}

/**
 * Performs a {@link queryOne} with the given arguments and returns matching node's
 * *content* (**value** or **inner text**).
 *
 * @param {Target} target
 * @param {QueryOptions} [options]
 * @returns {string}
 */
export function queryContent(target, options) {
    return getNodeContent(queryOne(target, options));
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
    if (Number.isInteger(options?.exact)) {
        throw new HootDomError(
            `cannot call \`queryOne\` with 'exact'=${options.exact}: did you mean to use \`queryAll\`?`
        );
    }
    return queryAll(target, { exact: 1, ...options })[0];
}

/**
 * @param {string} pseudoSelector
 * @param {PseudoSelectorPredicateBuilder} predicate
 */
export function registerPseudoSelector(pseudoSelector, predicate) {
    if (customPseudoSelectors.has(pseudoSelector)) {
        throw new HootDomError(
            `cannot register pseudo-selector: '${pseudoSelector}' already exists`
        );
    }
    customPseudoSelectors.set(pseudoSelector, predicate);
    customPseudoSelectorRegex = compilePseudoSelectorRegex();
}

/**
 * @param {number} width
 * @param {number} height
 */
export function setDimensions(width, height) {
    Object.assign(currentDimensions, { width, height });
    const defaultRoot = getDefaultRoot();
    if (width !== null) {
        defaultRoot.style.setProperty("width", `${width}px`, "important");
    }
    if (height !== null) {
        defaultRoot.style.setProperty("height", `${height}px`, "important");
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
    return options?.object ? parts : Object.values(parts).join("");
}

export function useFixture() {}

/**
 * Combination of {@link queryAll} and {@link waitUntil}: waits for a given target
 * to match elements in the DOM and returns the first matching node when it appears
 * (or immediatlly if it is already present).
 *
 * @see {@link queryAll}
 * @see {@link waitUntil}
 * @param {Target} target
 * @param {QueryOptions & WaitOptions} [options]
 * @returns {Promise<Node[]>}
 * @example
 *  const button = await waitFor(`button`);
 *  button.click();
 */
export function waitFor(target, options) {
    return waitUntil(() => queryAll(target, options)[0], {
        message: `Could not find "${target}" within %timeout% milliseconds`,
        ...options,
    });
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
export function waitUntil(predicate, options) {
    let disconnect = () => {};
    return new Promise((resolve, reject) => {
        const result = predicate();
        if (result) {
            return resolve(result);
        }

        const timeout = Math.floor(options?.timeout || 5_000);
        const message = options?.message || `'waitUntil' timed out after %timeout% milliseconds`;
        const timeoutId = setTimeout(
            () => reject(new HootDomError(message.replace("%timeout%", String(timeout)))),
            timeout
        );
        disconnect = observe(getDefaultRoot(), () => {
            const result = predicate();
            if (result) {
                resolve(result);
                clearTimeout(timeoutId);
            }
        });
    })
        .then((result) => {
            disconnect();
            return result;
        })
        .catch((reason) => {
            disconnect();
            throw reason;
        });
}

/**
 * Returns a function checking that the given target does not contain any child
 * node.
 *
 * @param {Document | Element | (() => Document | Element)} target
 * @returns {(cleanup: boolean) => void}
 * @example
 *  afterEach(watchChildren(document.body));
 */
export function watchChildren(target) {
    /**
     * @param {boolean} [cleanup=false]
     */
    return function checkChildren(cleanup = false) {
        if (typeof target === "function") {
            target = target();
        }
        if (!isInDOM(target)) {
            return;
        }
        const remainingElements = target?.childNodes.length;
        if (remainingElements) {
            if (cleanup) {
                target.innerHTML = "";
            } else {
                console.warn(
                    `${target.constructor.name} contains`,
                    remainingElements,
                    `undesired elements`
                );
            }
        }
    };
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
    const acceptedKeys = new Set([...Reflect.ownKeys(target), ...(whiteList || [])]);

    /**
     * @param {boolean} [cleanup=true]
     */
    return function checkKeys(cleanup = true) {
        if (!isInDOM(target)) {
            return;
        }
        const keysDiff = Reflect.ownKeys(target).filter(
            (key) => isNaN(key) && !acceptedKeys.has(key)
        );
        if (keysDiff.length) {
            if (cleanup) {
                for (const key of keysDiff) {
                    delete target[key];
                }
            } else {
                console.warn(
                    `${target.constructor.name} has`,
                    keysDiff.length,
                    `unexpected keys:`,
                    keysDiff
                );
            }
        }
    };
}
