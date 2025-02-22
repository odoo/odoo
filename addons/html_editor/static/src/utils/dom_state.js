import { isBlock } from "./blocks";
import { CTGROUPS, CTYPES, ctypeToString } from "./content_types";
import { isInPre, isVisible, isWhitespace, whitespace } from "./dom_info";
import {
    PATH_END_REASONS,
    ancestors,
    closestElement,
    closestPath,
    createDOMPathGenerator,
} from "./dom_traversal";
import { DIRECTIONS, leftPos, rightPos } from "./position";

const prepareUpdateLockedEditables = new Set();
/**
 * Any editor command is applied to a selection (collapsed or not). After the
 * command, the content type on the selection boundaries, in both direction,
 * should be preserved (some whitespace should disappear as went from collapsed
 * to non collapsed, or converted to &nbsp; as went from non collapsed to
 * collapsed, there also <br> to remove/duplicate, etc).
 *
 * This function returns a callback which allows to do that after the command
 * has been done.
 *
 * Note: the method has been made generic enough to work with non-collapsed
 * selection but can be used for an unique cursor position.
 *
 * @param {HTMLElement} el
 * @param {number} offset
 * @param {...(HTMLElement|number)} args - argument 1 and 2 can be repeated for
 *     multiple preparations with only one restore callback returned. Note: in
 *     that case, the positions should be given in the document node order.
 * @param {Object} [options]
 * @param {boolean} [options.allowReenter = true] - if false, all calls to
 *     prepareUpdate before this one gets restored will be ignored.
 * @param {string} [options.label = <random 6 character string>]
 * @param {boolean} [options.debug = false] - if true, adds nicely formatted
 *     console logs to help with debugging.
 * @returns {function}
 */
export function prepareUpdate(...args) {
    const closestRoot =
        args.length &&
        ancestors(args[0]).find((ancestor) => ancestor.classList.contains("odoo-editor-editable"));
    const isPrepareUpdateLocked = closestRoot && prepareUpdateLockedEditables.has(closestRoot);
    const hash = (Math.random() + 1).toString(36).substring(7);
    const options = {
        allowReenter: true,
        label: hash,
        debug: false,
        ...(args.length && args[args.length - 1] instanceof Object ? args.pop() : {}),
    };
    if (options.debug) {
        console.log(
            "%cPreparing%c update: " +
                options.label +
                (options.label === hash ? "" : ` (${hash})`) +
                "%c" +
                (isPrepareUpdateLocked ? " LOCKED" : ""),
            "color: cyan;",
            "color: white;",
            "color: red; font-weight: bold;"
        );
    }
    if (isPrepareUpdateLocked) {
        return () => {
            if (options.debug) {
                console.log(
                    "%cRestoring%c update: " +
                        options.label +
                        (options.label === hash ? "" : ` (${hash})`) +
                        "%c LOCKED",
                    "color: lightgreen;",
                    "color: white;",
                    "color: red; font-weight: bold;"
                );
            }
        };
    }
    if (!options.allowReenter && closestRoot) {
        prepareUpdateLockedEditables.add(closestRoot);
    }
    const positions = [...args];

    // Check the state in each direction starting from each position.
    const restoreData = [];
    let el, offset;
    while (positions.length) {
        // Note: important to get the positions in reverse order to restore
        // right side before left side.
        offset = positions.pop();
        el = positions.pop();
        const left = getState(el, offset, DIRECTIONS.LEFT);
        const right = getState(el, offset, DIRECTIONS.RIGHT, left.cType);
        if (options.debug) {
            const editable = el && closestElement(el, ".odoo-editor-editable");
            const oldEditableHTML =
                (editable && editable.innerHTML.replaceAll(" ", "_").replaceAll("\u200B", "ZWS")) ||
                "";
            left.oldEditableHTML = oldEditableHTML;
            right.oldEditableHTML = oldEditableHTML;
        }
        restoreData.push(left, right);
    }

    // Create the callback that will be able to restore the state in each
    // direction wherever the node in the opposite direction has landed.
    return function restoreStates() {
        if (options.debug) {
            console.log(
                "%cRestoring%c update: " +
                    options.label +
                    (options.label === hash ? "" : ` (${hash})`),
                "color: lightgreen;",
                "color: white;"
            );
        }
        for (const data of restoreData) {
            restoreState(data, options.debug);
        }
        if (!options.allowReenter && closestRoot) {
            prepareUpdateLockedEditables.delete(closestRoot);
        }
    };
}

export const leftLeafOnlyNotBlockPath = createDOMPathGenerator(DIRECTIONS.LEFT, {
    leafOnly: true,
    stopTraverseFunction: isBlock,
    stopFunction: isBlock,
});

const rightLeafOnlyNotBlockPath = createDOMPathGenerator(DIRECTIONS.RIGHT, {
    leafOnly: true,
    stopTraverseFunction: isBlock,
    stopFunction: isBlock,
});

/**
 * Retrieves the "state" from a given position looking at the given direction.
 * The "state" is the type of content. The functions also returns the first
 * meaninful node looking in the opposite direction = the first node we trust
 * will not disappear if a command is played in the given direction.
 *
 * Note: only work for in-between nodes positions. If the position is inside a
 * text node, first split it @see splitTextNode.
 *
 * @param {HTMLElement} el
 * @param {number} offset
 * @param {boolean} direction @see DIRECTIONS.LEFT @see DIRECTIONS.RIGHT
 * @param {CTYPES} [leftCType]
 * @returns {Object}
 */
export function getState(el, offset, direction, leftCType) {
    const leftDOMPath = leftLeafOnlyNotBlockPath;
    const rightDOMPath = rightLeafOnlyNotBlockPath;

    let domPath;
    let inverseDOMPath;
    const whitespaceAtStartRegex = new RegExp("^" + whitespace + "+");
    const whitespaceAtEndRegex = new RegExp(whitespace + "+$");
    const reasons = [];
    if (direction === DIRECTIONS.LEFT) {
        domPath = leftDOMPath(el, offset, reasons);
        inverseDOMPath = rightDOMPath(el, offset);
    } else {
        domPath = rightDOMPath(el, offset, reasons);
        inverseDOMPath = leftDOMPath(el, offset);
    }

    // TODO I think sometimes, the node we have to consider as the
    // anchor point to restore the state is not the first one of the inverse
    // path (like for example, empty text nodes that may disappear
    // after the command so we would not want to get those ones).
    const boundaryNode = inverseDOMPath.next().value;

    // We only traverse through deep inline nodes. If we cannot find a
    // meanfingful state between them, that means we hit a block.
    let cType = undefined;

    // Traverse the DOM in the given direction to check what type of content
    // there is.
    let lastSpace = null;
    for (const node of domPath) {
        if (node.nodeType === Node.TEXT_NODE) {
            const value = node.nodeValue;
            // If we hit a text node, the state depends on the path direction:
            // any space encountered backwards is a visible space if we hit
            // visible content afterwards. If going forward, spaces are only
            // visible if we have content backwards.
            if (direction === DIRECTIONS.LEFT) {
                if (!isWhitespace(value)) {
                    if (lastSpace) {
                        cType = CTYPES.SPACE;
                    } else {
                        const rightLeaf = rightLeafOnlyNotBlockPath(node).next().value;
                        const hasContentRight =
                            rightLeaf && !whitespaceAtStartRegex.test(rightLeaf.textContent);
                        cType =
                            !hasContentRight && whitespaceAtEndRegex.test(node.textContent)
                                ? CTYPES.SPACE
                                : CTYPES.CONTENT;
                    }
                    break;
                }
                if (value.length) {
                    lastSpace = node;
                }
            } else {
                leftCType = leftCType || getState(el, offset, DIRECTIONS.LEFT).cType;
                if (whitespaceAtStartRegex.test(value)) {
                    const leftLeaf = leftLeafOnlyNotBlockPath(node).next().value;
                    const hasContentLeft =
                        leftLeaf && !whitespaceAtEndRegex.test(leftLeaf.textContent);
                    const rct = !isWhitespace(value)
                        ? CTYPES.CONTENT
                        : getState(...rightPos(node), DIRECTIONS.RIGHT).cType;
                    cType =
                        leftCType & CTYPES.CONTENT &&
                        rct & (CTYPES.CONTENT | CTYPES.BR) &&
                        !hasContentLeft
                            ? CTYPES.SPACE
                            : rct;
                    break;
                }
                if (!isWhitespace(value)) {
                    cType = CTYPES.CONTENT;
                    break;
                }
            }
        } else if (node.nodeName === "BR") {
            cType = CTYPES.BR;
            break;
        } else if (isVisible(node)) {
            // E.g. an image
            cType = CTYPES.CONTENT;
            break;
        }
    }

    if (cType === undefined) {
        cType = reasons.includes(PATH_END_REASONS.BLOCK_HIT)
            ? CTYPES.BLOCK_OUTSIDE
            : CTYPES.BLOCK_INSIDE;
    }

    return {
        node: boundaryNode,
        direction: direction,
        cType: cType, // Short for contentType
    };
}
const priorityRestoreStateRules = [
    // Each entry is a list of two objects, with each key being optional (the
    // more key-value pairs, the bigger the priority).
    // {direction: ..., cType1: ..., cType2: ...}
    // ->
    // {spaceVisibility: (false|true), brVisibility: (false|true)}
    [
        // Replace a space by &nbsp; when it was not collapsed before and now is
        // collapsed (one-letter word removal for example).
        { cType1: CTYPES.CONTENT, cType2: CTYPES.SPACE | CTGROUPS.BLOCK },
        { spaceVisibility: true },
    ],
    [
        // Replace a space by &nbsp; when it was content before and now it is
        // a BR.
        { direction: DIRECTIONS.LEFT, cType1: CTGROUPS.INLINE, cType2: CTGROUPS.BR },
        { spaceVisibility: true },
    ],
    [
        // Replace a space by &nbsp; when it was content before and now it is
        // a BR (removal of last character before a BR for example).
        { direction: DIRECTIONS.RIGHT, cType1: CTGROUPS.CONTENT, cType2: CTGROUPS.BR },
        { spaceVisibility: true },
    ],
    [
        // Replace a space by &nbsp; when it was visible thanks to a BR which
        // is now gone.
        { direction: DIRECTIONS.RIGHT, cType1: CTGROUPS.BR, cType2: CTYPES.SPACE | CTGROUPS.BLOCK },
        { spaceVisibility: true },
    ],
    [
        // Remove all collapsed spaces when a space is removed.
        { cType1: CTYPES.SPACE },
        { spaceVisibility: false },
    ],
    [
        // Remove spaces once the preceeding BR is removed
        { direction: DIRECTIONS.LEFT, cType1: CTGROUPS.BR },
        { spaceVisibility: false },
    ],
    [
        // Remove space before block once content is put after it (otherwise it
        // would become visible).
        { cType1: CTGROUPS.BLOCK, cType2: CTGROUPS.INLINE | CTGROUPS.BR },
        { spaceVisibility: false },
    ],
    [
        // Duplicate a BR once the content afterwards disappears
        { direction: DIRECTIONS.RIGHT, cType1: CTGROUPS.INLINE, cType2: CTGROUPS.BLOCK },
        { brVisibility: true },
    ],
    [
        // Remove a BR at the end of a block once inline content is put after
        // it (otherwise it would act as a line break).
        {
            direction: DIRECTIONS.RIGHT,
            cType1: CTGROUPS.BLOCK,
            cType2: CTGROUPS.INLINE | CTGROUPS.BR,
        },
        { brVisibility: false },
    ],
    [
        // Remove a BR once the BR that preceeds it is now replaced by
        // content (or if it was a BR at the start of a block which now is
        // a trailing BR).
        {
            direction: DIRECTIONS.LEFT,
            cType1: CTGROUPS.BR | CTGROUPS.BLOCK,
            cType2: CTGROUPS.INLINE,
        },
        { brVisibility: false, extraBRRemovalCondition: (brNode) => isFakeLineBreak(brNode) },
    ],
];
function restoreStateRuleHashCode(direction, cType1, cType2) {
    return `${direction}-${cType1}-${cType2}`;
}
const allRestoreStateRules = (function () {
    const map = new Map();

    const keys = ["direction", "cType1", "cType2"];
    for (const direction of Object.values(DIRECTIONS)) {
        for (const cType1 of Object.values(CTYPES)) {
            for (const cType2 of Object.values(CTYPES)) {
                const rule = { direction: direction, cType1: cType1, cType2: cType2 };

                // Search for the rules which match whatever their priority
                const matchedRules = [];
                for (const entry of priorityRestoreStateRules) {
                    let priority = 0;
                    for (const key of keys) {
                        const entryKeyValue = entry[0][key];
                        if (entryKeyValue !== undefined) {
                            if (
                                typeof entryKeyValue === "boolean"
                                    ? rule[key] === entryKeyValue
                                    : rule[key] & entryKeyValue
                            ) {
                                priority++;
                            } else {
                                priority = -1;
                                break;
                            }
                        }
                    }
                    if (priority >= 0) {
                        matchedRules.push([priority, entry[1]]);
                    }
                }

                // Create the final rule by merging found rules by order of
                // priority
                const finalRule = {};
                for (let p = 0; p <= keys.length; p++) {
                    for (const entry of matchedRules) {
                        if (entry[0] === p) {
                            Object.assign(finalRule, entry[1]);
                        }
                    }
                }

                // Create an unique identifier for the set of values
                // direction - state 1 - state2 to add the rule in the map
                const hashCode = restoreStateRuleHashCode(direction, cType1, cType2);
                map.set(hashCode, finalRule);
            }
        }
    }

    return map;
})();
/**
 * Restores the given state starting before the given while looking in the given
 * direction.
 *
 * @param {Object} prevStateData @see getState
 * @param {boolean} debug=false - if true, adds nicely formatted
 *     console logs to help with debugging.
 * @returns {Object|undefined} the rule that was applied to restore the state,
 *     if any, for testing purposes.
 */
export function restoreState(prevStateData, debug = false) {
    const { node, direction, cType: cType1, oldEditableHTML } = prevStateData;
    if (!node || !node.parentNode) {
        // FIXME sometimes we want to restore the state starting from a node
        // which has been removed by another restoreState call... Not sure if
        // it is a problem or not, to investigate.
        return;
    }
    const [el, offset] = direction === DIRECTIONS.LEFT ? leftPos(node) : rightPos(node);
    const { cType: cType2 } = getState(el, offset, direction);

    /**
     * Knowing the old state data and the new state data, we know if we have to
     * do something or not, and what to do.
     */
    const ruleHashCode = restoreStateRuleHashCode(direction, cType1, cType2);
    const rule = allRestoreStateRules.get(ruleHashCode);
    if (debug) {
        const editable = closestElement(node, ".odoo-editor-editable");
        console.log(
            "%c" +
                node.textContent.replaceAll(" ", "_").replaceAll("\u200B", "ZWS") +
                "\n" +
                "%c" +
                (direction === DIRECTIONS.LEFT ? "left" : "right") +
                "\n" +
                "%c" +
                ctypeToString(cType1) +
                "\n" +
                "%c" +
                ctypeToString(cType2) +
                "\n" +
                "%c" +
                "BEFORE: " +
                (oldEditableHTML || "(unavailable)") +
                "\n" +
                "%c" +
                "AFTER:  " +
                (editable
                    ? editable.innerHTML.replaceAll(" ", "_").replaceAll("\u200B", "ZWS")
                    : "(unavailable)") +
                "\n",
            "color: white; display: block; width: 100%;",
            "color: " +
                (direction === DIRECTIONS.LEFT ? "magenta" : "lightgreen") +
                "; display: block; width: 100%;",
            "color: pink; display: block; width: 100%;",
            "color: lightblue; display: block; width: 100%;",
            "color: white; display: block; width: 100%;",
            "color: white; display: block; width: 100%;",
            rule
        );
    }
    if (Object.values(rule).filter((x) => x !== undefined).length) {
        const inverseDirection = direction === DIRECTIONS.LEFT ? DIRECTIONS.RIGHT : DIRECTIONS.LEFT;
        enforceWhitespace(el, offset, inverseDirection, rule);
    }
    return rule;
}

/**
 * Returns whether or not the given node is a BR element which does not really
 * act as a line break, but as a placeholder for the cursor or to make some left
 * element (like a space) visible.
 * @todo @phoenix this depends on state, so hard to move it to dom_info
 *
 * @param {HTMLBRElement} brEl
 * @returns {boolean}
 */
export function isFakeLineBreak(brEl) {
    return !(getState(...rightPos(brEl), DIRECTIONS.RIGHT).cType & (CTYPES.CONTENT | CTGROUPS.BR));
}

/**
 * Enforces the whitespace and BR visibility in the given direction starting
 * from the given position.
 *
 * @param {HTMLElement} el
 * @param {number} offset
 * @param {number} direction @see DIRECTIONS.LEFT @see DIRECTIONS.RIGHT
 * @param {Object} rule
 * @param {boolean} [rule.spaceVisibility]
 * @param {boolean} [rule.brVisibility]
 */
export function enforceWhitespace(el, offset, direction, rule) {
    const document = el.ownerDocument;
    let domPath, whitespaceAtEdgeRegex;
    if (direction === DIRECTIONS.LEFT) {
        domPath = leftLeafOnlyNotBlockPath(el, offset);
        whitespaceAtEdgeRegex = new RegExp(whitespace + "+$");
    } else {
        domPath = rightLeafOnlyNotBlockPath(el, offset);
        whitespaceAtEdgeRegex = new RegExp("^" + whitespace + "+");
    }

    const invisibleSpaceTextNodes = [];
    let foundVisibleSpaceTextNode = null;
    for (const node of domPath) {
        if (node.nodeName === "BR") {
            if (rule.brVisibility === undefined) {
                break;
            }
            if (rule.brVisibility) {
                node.before(document.createElement("br"));
            } else {
                if (!rule.extraBRRemovalCondition || rule.extraBRRemovalCondition(node)) {
                    node.remove();
                }
            }
            break;
        } else if (node.nodeType === Node.TEXT_NODE && !isInPre(node)) {
            if (whitespaceAtEdgeRegex.test(node.nodeValue)) {
                // If we hit spaces going in the direction, either they are in a
                // visible text node and we have to change the visibility of
                // those spaces, or it is in an invisible text node. In that
                // last case, we either remove the spaces if there are spaces in
                // a visible text node going further in the direction or we
                // change the visiblity or those spaces.
                if (!isWhitespace(node)) {
                    foundVisibleSpaceTextNode = node;
                    break;
                } else {
                    invisibleSpaceTextNodes.push(node);
                }
            } else if (!isWhitespace(node)) {
                break;
            }
        } else {
            break;
        }
    }

    if (rule.spaceVisibility === undefined) {
        return;
    }
    if (!rule.spaceVisibility) {
        for (const node of invisibleSpaceTextNodes) {
            // Empty and not remove to not mess with offset-based positions in
            // commands implementation, also remove non-block empty parents.
            node.nodeValue = "";
            const ancestorPath = closestPath(node.parentNode);
            let toRemove = null;
            for (const pNode of ancestorPath) {
                if (toRemove) {
                    toRemove.remove();
                }
                if (pNode.childNodes.length === 1 && !isBlock(pNode)) {
                    pNode.after(node);
                    toRemove = pNode;
                } else {
                    break;
                }
            }
        }
    }
    const spaceNode = foundVisibleSpaceTextNode || invisibleSpaceTextNodes[0];
    if (spaceNode) {
        let spaceVisibility = rule.spaceVisibility;
        // In case we are asked to replace the space by a &nbsp;, disobey and
        // do the opposite if that space is currently not visible
        // TODO I'd like this to not be needed, it feels wrong...
        if (
            spaceVisibility &&
            !foundVisibleSpaceTextNode &&
            getState(...rightPos(spaceNode), DIRECTIONS.RIGHT).cType & CTGROUPS.BLOCK &&
            getState(...leftPos(spaceNode), DIRECTIONS.LEFT).cType !== CTYPES.CONTENT
        ) {
            spaceVisibility = false;
        }
        spaceNode.nodeValue = spaceNode.nodeValue.replace(
            whitespaceAtEdgeRegex,
            spaceVisibility ? "\u00A0" : ""
        );
    }
}

/**
 * Call this function to start watching for mutations.
 * Call the returned function to stop watching and get the mutation records.
 *
 * @returns {() => MutationRecord[]}
 */
export function observeMutations(target, observerOptions) {
    const records = [];
    const observerCallback = (mutations) => records.push(...mutations);
    const observer = new MutationObserver(observerCallback);
    observer.observe(target, observerOptions);
    return () => {
        observerCallback(observer.takeRecords());
        observer.disconnect();
        return records;
    };
}
