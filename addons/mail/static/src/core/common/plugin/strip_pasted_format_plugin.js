import { Plugin } from "@html_editor/plugin";
import { isBlock } from "@html_editor/utils/blocks";
import { unwrapContents } from "@html_editor/utils/dom";
import { PRESERVED_CLASSNAMES } from "@mail/core/common/plugin/mail_composer_plugin";

const FORMAT_SELECTOR = "b, strong, i, em, u, s";
const LINK_SELECTOR = `a:not(${[...PRESERVED_CLASSNAMES].map((c) => `.${c}`).join(", ")})`;
const LIST_SELECTOR = "ul, ol";
const LINE_END = Symbol("lineEnd");

/**
 * Whether the node holds content that would end up on the same line as a list
 * replaced by its lines.
 *
 * @param {Node|null} node
 */
function isInlineContent(node) {
    return node?.nodeType === Node.TEXT_NODE ? !!node.textContent.trim() : !!node && !isBlock(node);
}

/**
 * Pasted or dropped content is reduced to text and mentions, like in a textarea.
 *
 * Links are replaced by their text, as they couldn't be removed.
 */
export class StripPastedFormatPlugin extends Plugin {
    static id = "stripPastedFormat";
    /** @type {import("plugins").EditorResources} */
    resources = {
        // Paste and drop both end up inserting through the dom plugin.
        fragment_to_insert_processors: (fragment) => {
            for (const el of fragment.querySelectorAll(`${FORMAT_SELECTOR}, ${LINK_SELECTOR}`)) {
                unwrapContents(el);
            }
            for (const list of fragment.querySelectorAll(LIST_SELECTOR)) {
                // Nested lists are flattened along with their outermost list.
                if (fragment.contains(list)) {
                    this.replaceListByLines(list);
                }
            }
            return fragment;
        },
    };

    /**
     * Replace the list by the content of its items (and of its nested lists),
     * one item per line, like the list would be pasted as text in a textarea.
     *
     * @param {HTMLUListElement|HTMLOListElement} list
     */
    replaceListByLines(list) {
        const lines = this.getListLines(list);
        const nodes = lines.flatMap((line) => [this.document.createElement("br"), ...line]);
        if (!isInlineContent(list.previousSibling)) {
            nodes.shift();
        }
        if (isInlineContent(list.nextSibling)) {
            nodes.push(this.document.createElement("br"));
        }
        list.replaceWith(...nodes);
    }

    /**
     * @param {HTMLUListElement|HTMLOListElement} list
     * @returns {Node[][]}
     */
    getListLines(list) {
        const lines = [];
        for (const item of list.children) {
            let line;
            const nodes = [...item.childNodes];
            while (nodes.length) {
                const node = nodes.shift();
                if (node === LINE_END) {
                    line = undefined;
                } else if (node.matches?.(LIST_SELECTOR)) {
                    lines.push(...this.getListLines(node));
                    line = undefined;
                } else if (isBlock(node)) {
                    // e.g. <li><p>...</p></li>: the block content is its own line.
                    nodes.unshift(LINE_END, ...node.childNodes, LINE_END);
                } else if (line || isInlineContent(node)) {
                    if (!line) {
                        line = [];
                        lines.push(line);
                    }
                    line.push(node);
                }
            }
        }
        return lines;
    }
}
