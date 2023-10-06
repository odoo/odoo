/** @odoo-module **/

import * as OdooEditorLib from "@web_editor/js/editor/odoo-editor/src/utils/utils";

// SVG generator: contains all information needed to draw highlight SVGs
// according to text dimensions, highlight style,...
const _textHighlightFactory = {
    underline: targetEl => {
        return drawPath(targetEl, {mode: "line"});
    },
    freehand: targetEl => {
        const template = (w, h) => [`M 0,${h * 1.1} C ${w / 8},${h * 1.05} ${w / 4},${h} ${w},${h}`];
        return drawPath(targetEl, {mode: "free", template});
    },
    double: targetEl => {
        const template = (w, h) => [
            `M 0,${h * 0.9} h ${w}`,
            `M 0,${h * 1.1} h ${w}`,
        ];
        return drawPath(targetEl, {mode: "free", template});
    },
    wavy: targetEl => {
        const template = (w, h) => [
            `c ${w / 4},0 ${w / 4},-${h / 2} ${w / 2},-${h / 2}` +
            `c ${w / 4},0 ${w / 4},${h / 2} ${w / 2},${h / 2}`
        ];
        return drawPath(targetEl, {mode: "pattern", template});
    },
    circle: targetEl => {
        const template = (w, h) => [
            `M ${w / 2.88},${h / 1.1} C ${w / 1.1},${h / 1.05} ${w * 1.05},${h / 1.1} ${w * 1.023},${h / 2.32}` +
            `C ${w}, ${h / 14.6} ${w / 1.411},0 ${w / 2},0 S -2,${h / 14.6} -2,${h / 2.2}` +
            `S ${w / 4.24},${h} ${w / 1.36},${h * 1.04}`
        ];
        return drawPath(targetEl, {mode: "free", template});
    },
    over_underline: targetEl => {
        const template = (w, h) => [
            `M 0,0 h ${w}`,
            `M 0,${h} h ${w}`,
        ];
        return drawPath(targetEl, {mode: "free", template});
    },
    scribble: targetEl => {
        const template = (w, h) => [
            `M ${w / 2},${h * 0.9} c ${w / 16},0 ${w},1 ${w / 5},1 c 2,0 -${w / 10},-2 -${w / 2},-1` +
            `c -${w / 20},0 -${w / 5},2 -${w / 5},4 c -2,0 ${w / 10},-1 ${w / 2},${h / 16}` +
            `c ${w / 25},0 ${w / 10},0 ${w / 5},1 c 0,0 -${w / 10},1 -${w / 8},1` +
            `c -${w / 40},0 -${w / 16},0 -${w / 4},${h / 22}`
        ];
        return drawPath(targetEl, {mode: "free", template});
    },
    jagged: targetEl => {
        const template = (w, h) => [
            `q ${4 * w / 3} -${2 * w / 3} ${2 * w / 3} 0` +
            `c -${w / 3} ${w / 3} -${w / 3} ${w / 3} ${w / 3} 0`
        ];
        return drawPath(targetEl, {mode: "pattern", template});
    },
    cross: targetEl => {
        const template = (w, h) => [
            `M 0,0 L ${w},${h}`,
            `M 0,${h} L ${w},0`,
        ];
        return drawPath(targetEl, {mode: "free", template});
    },
    diagonal: targetEl => {
        const template = (w, h) => [`M 0,${h} L${w},0`];
        return drawPath(targetEl, {mode: "free", template});
    },
    strikethrough: targetEl => {
        return drawPath(targetEl, {mode: "line", position: "center"});
    },
};
// Returns the width of the DOMRect object.
export const getDOMRectWidth = el => el.getBoundingClientRect().width;

/**
 * Draws one or many SVG paths using templates of path shape commands.
 *
 * @param {HTMLElement} textEl
 * @param {String} options.mode Specifies how to draw the path:
 * - "pattern": repeat the template along the horizontal axis.
 * - "line": draw a simple line (we specify the width & position).
 * - "free": draw the path shape using the template only.
 * @param {Function} options.template Returns a list of SVG path
 * commands adapted to the container's size.
 * @returns {String[]}
 */
function drawPath(textEl, options) {
    const {width, height} = textEl.getBoundingClientRect();
    const yStart = options.position === "center" ? height / 2 : height;

    switch (options.mode) {
        case "pattern": {
            let i = 0, d = [];
            const nbrChars = textEl.textContent.length;
            const w = width / nbrChars, h = height * 0.2;
            while (i < nbrChars) {
                d.push(options.template(w, h));
                i++;
            }
            return [`M 0,${yStart} ${d.join(" ")}`];
        }
        case "line": {
            return [`M 0,${yStart} h ${width}`];
        }
    }
    return options.template(width, height);
}

/**
 * Returns a new highlight SVG adapted to the text container.
 *
 * @param {HTMLElement} textEl
 * @param {String} highlightID
 */
export function drawTextHighlightSVG(textEl, highlightID) {
    const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    svg.setAttribute("fill", "none");
    svg.classList.add(
        "o_text_highlight_svg",
        // Identifies DOM content that should not be merged by the editor, even
        // on identical parents.
        "o_content_no_merge",
        "position-absolute",
        "overflow-visible",
        "top-0",
        "start-0",
        "w-100",
        "h-100",
        "pe-none");
    _textHighlightFactory[highlightID](textEl).forEach(d => {
        const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
        path.classList.add(`o_text_highlight_path_${highlightID}`);
        path.setAttribute("stroke-linecap", "round");
        path.setAttribute("stroke", "var(--text-highlight-color)");
        path.setAttribute("stroke-width", "var(--text-highlight-width)");
        path.setAttribute("d", d);
        svg.appendChild(path);
    });
    return svg;
}

/**
 * Divides the content of a text container into multiple
 * `.o_text_highlight_item` units, and applies the highlight
 * on each unit.
 *
 * @param {HTMLElement} topTextEl
 * @param {String} highlightID
 */
export function applyTextHighlight(topTextEl, highlightID) {
    const lines = [];
    let lineIndex = 0;
    const nodeIsBR = node => node.nodeName === "BR";
    const isRTL = el => window.getComputedStyle(el).direction === "rtl";

    [...topTextEl.childNodes].forEach(child => {
        // We consider `<br/>` tags as full text lines to ease
        // excluding them when the highlight is applied on the DOM.
        if (nodeIsBR(child)) {
            lines[++lineIndex] = [child];
            return lineIndex++;
        }
        const textLines = splitNodeLines(child);

        // Special case: The text lines detection code in `splitNodeLines()`
        // (based on `getClientRects()`) can't handle a situation when a line
        // exactly ends with the current child node. We need to handle this
        // manually by checking if the current child node is the last one in
        // the line (taking into account the RTL direction).
        // TODO: Improve this.
        let lastNodeInLine = false;
        if (child.textContent && child.nextSibling?.textContent) {
            const range = document.createRange();
            const lastCurrentText = selectAllTextNodes(child).at(-1);
            range.setStart(lastCurrentText, lastCurrentText.length - 1);
            range.setEnd(lastCurrentText, lastCurrentText.length);
            // Get the "END" position of the last text node in current child.
            const currentEnd = range.getBoundingClientRect()[isRTL(topTextEl) ? "left" : "right"];
            const firstnextText = selectAllTextNodes(child.nextSibling)[0];
            range.setStart(firstnextText, 0);
            range.setEnd(firstnextText, 1);
            // Get the "START" position of the first text node in the next
            // sibling.
            const nextStart = range.getBoundingClientRect()[isRTL(topTextEl) ? "right" : "left"];
            // The next sibling starts before the end of the current node
            // => Line break detected.
            lastNodeInLine = nextStart + 1 < currentEnd;
        }

        // for each text line detected, we add the content as new
        // line and adjust the line index accordingly.
        textLines.map((node, i, {length}) => {
            if (!lines[lineIndex]) {
                lines[lineIndex] = [];
            }
            lines[lineIndex].push(node);
            if (i !== length - 1 || lastNodeInLine) {
                lineIndex++;
            }
        });
    });
    topTextEl.replaceChildren(...lines.map(textLine => {
        // First we add text content to be able to build svg paths
        // correctly (`<br/>` tags are excluded).
        return nodeIsBR(textLine[0]) ? textLine[0] :
            createHighlightContainer(textLine);
    }));
    // Build and set highlight SVGs.
    [...topTextEl.querySelectorAll(".o_text_highlight_item")].forEach(container => {
        container.append(drawTextHighlightSVG(container, highlightID));
    });
}

/**
 * Used to rollback the @see applyTextHighlight behaviour.
 *
 * @param {HTMLElement} topTextEl
 */
export function removeTextHighlight(topTextEl) {
    // Simply replace every `<span class="o_text_highlight_item">
    // textNode1 [textNode2,...]<svg .../></span>` by `textNode1
    // [textNode2,...]`.
    [...topTextEl.querySelectorAll(".o_text_highlight_item")].forEach(unit => {
        unit.after(...[...unit.childNodes].filter((node) => node.tagName !== "svg"));
        unit.remove();
    });
    // Prevents incorrect text lines detection on the next updates.
    let child = topTextEl.firstElementChild;
    while (child) {
        let next = child.nextElementSibling;
        // Merge identical elements.
        if (next && next === child.nextSibling && child.cloneNode().isEqualNode(next.cloneNode())) {
            child.replaceChildren(...child.childNodes, ...next.childNodes);
            next.remove();
        } else {
            child = next;
        }
    }
    topTextEl.normalize();
}

/**
 * Used to change or adjust the highlight effect when it's needed (E.g. on
 * window / text container "resize").
 *
 * @param {HTMLElement} textEl The top text highlight element.
 * @param {String} highlightID The new highlight to apply (or the old one
 * if we just want to adapt the effect).
 */
export function switchTextHighlight(textEl, highlightID) {
    const ownerDocument = textEl.ownerDocument;
    const sel = ownerDocument.getSelection();
    const restoreSelection = sel.rangeCount === 1 && textEl.contains(sel.anchorNode);
    let rangeCollapsed,
    cursorEndPosition = 0,
    rangeSize = 0;

    // Because of text highlight adaptations, the selection offset will
    // be lost, which will cause issues when typing and deleting text...
    // The goal here is to preserve the selection to restore it for the
    // new elements after the update when it's needed.
    if (restoreSelection) {
        const range = sel.getRangeAt(0);
        rangeSize = range.toString().length;
        rangeCollapsed = range.collapsed;
        // We need the position related to the `.o_text_highlight` element.
        const globalRange = range.cloneRange();
        globalRange.selectNodeContents(textEl);
        globalRange.setEnd(range.endContainer, range.endOffset);
        cursorEndPosition = globalRange.toString().length;
    }

    // Set the new text highlight effect.
    if (highlightID) {
        removeTextHighlight(textEl);
        applyTextHighlight(textEl, highlightID);
    }

    // Restore the old selection.
    if (restoreSelection && cursorEndPosition) {
        if (rangeCollapsed) {
            const selectionOffset = getOffsetNode(textEl, cursorEndPosition);
            OdooEditorLib.setSelection(...selectionOffset, ...selectionOffset);
        } else {
            OdooEditorLib.setSelection(
                ...getOffsetNode(textEl, cursorEndPosition - rangeSize),
                ...getOffsetNode(textEl, cursorEndPosition)
            );
        }
        ownerDocument.dispatchEvent(new Event("selectionchange"));
    }
}

/**
 * Used to wrap text nodes in a single "text highlight" unit.
 *
 * @param {Node[]} nodes
 * @returns {HTMLElement} The one line text element that should contain
 * the highlight SVG.
 */
function createHighlightContainer(nodes) {
    const highlightContainer = document.createElement("span");
    highlightContainer.className = "o_text_highlight_item";
    highlightContainer.append(...nodes);
    return highlightContainer;
}

/**
 * Used to get the current text highlight id from the top `.o_text_highlight`
 * container class.
 *
 * @param {HTMLElement} el
 * @returns {String}
 */
export function getCurrentTextHighlight(el) {
    const topTextEl = el.closest(".o_text_highlight");
    const match = topTextEl?.className.match(/o_text_highlight_(?<value>[\w]+)/);
    let highlight = "";
    if (match) {
        highlight = match.groups.value;
    }
    return highlight;
}

/**
 * Returns a list of detected lines in the content of a text node.
 *
 * @param {Node} node
 */
function splitNodeLines(node) {
    const isTextContainer = node.childNodes.length === 1
        && node.firstChild.nodeType === Node.TEXT_NODE;
    if (node.nodeType !== Node.TEXT_NODE && !isTextContainer) {
        return [node];
    }
    const text = node.textContent;
    const textNode = isTextContainer ? node.firstChild : node;
    const lines = [];
    const range = document.createRange();
    let i = -1;
    while (++i < text.length) {
        range.setStart(textNode, 0);
        range.setEnd(textNode, i + 1);
        const clientRects = range.getClientRects().length || 1;
        const lineIndex = clientRects - 1;
        const currentText = lines[lineIndex];
        lines[lineIndex] = (currentText || "") + text.charAt(i);
    }
    // Return the original node when no lines were detected.
    if (lines.length === 1) {
        return [node];
    }
    return lines.map(line => {
        if (isTextContainer) {
            const wrapper = node.cloneNode();
            wrapper.appendChild(document.createTextNode(line));
            return wrapper;
        }
        return document.createTextNode(line);
    });
}

/**
 * Get all text nodes inside a parent DOM element.
 *
 * @param {Node} topNode
 * @returns {Node[]} List of text "childNodes" or the element itself
 * (if it's a text node).
 */
export function selectAllTextNodes(topNode) {
    const textNodes = [];
    const selectTextNodes = (node) => {
        if (node.nodeType === Node.TEXT_NODE) {
            textNodes.push(node);
        } else {
            [...node.childNodes].forEach(child => selectTextNodes(child));
        }
    };
    selectTextNodes(topNode);
    return textNodes;
}

/**
 * Used to get the node of a text element in which a selection starts/ends.
 *
 * @param {HTMLElement} textEl The parent text element.
 * @param {Number} offset The selection offset in parent element.
 * @returns {[Node, Number]} The node found in the cursor position
 * and the new offset compared to that node.
 */
export function getOffsetNode(textEl, offset) {
    let index = 0,
    offsetNode;
    for (const node of selectAllTextNodes(textEl)) {
        const stepLength = node.textContent.length;
        if (index + stepLength < offset - 1) {
            index += stepLength;
        } else {
            offsetNode = node;
            break;
        }
    }
    return [offsetNode, offset - index];
}
