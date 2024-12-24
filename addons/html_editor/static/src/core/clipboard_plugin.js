import { isTextNode, paragraphRelatedElements } from "../utils/dom_info";
import { Plugin } from "../plugin";
import { closestBlock, isBlock } from "../utils/blocks";
import { unwrapContents } from "../utils/dom";
import { ancestors, childNodes, closestElement } from "../utils/dom_traversal";
import { parseHTML } from "../utils/html";

/**
 * @typedef { import("./selection_plugin").EditorSelection } EditorSelection
 */

const CLIPBOARD_BLACKLISTS = {
    unwrap: [".Apple-interchange-newline", "DIV"], // These elements' children will be unwrapped.
    remove: ["META", "STYLE", "SCRIPT"], // These elements will be removed along with their children.
};
export const CLIPBOARD_WHITELISTS = {
    nodes: [
        // Style
        "P",
        "H1",
        "H2",
        "H3",
        "H4",
        "H5",
        "H6",
        "BLOCKQUOTE",
        "PRE",
        // List
        "UL",
        "OL",
        "LI",
        // Inline style
        "I",
        "B",
        "U",
        "S",
        "EM",
        "FONT",
        "STRONG",
        // Table
        "TABLE",
        "THEAD",
        "TH",
        "TBODY",
        "TR",
        "TD",
        // Miscellaneous
        "IMG",
        "BR",
        "A",
        ".fa",
    ],
    classes: [
        // Media
        /^float-/,
        "d-block",
        "mx-auto",
        "img-fluid",
        "img-thumbnail",
        "rounded",
        "rounded-circle",
        "table",
        "table-bordered",
        /^padding-/,
        /^shadow/,
        // Odoo colors
        /^text-o-/,
        /^bg-o-/,
        // Odoo lists
        "o_checked",
        "o_checklist",
        "oe-nested",
        // Miscellaneous
        /^btn/,
        /^fa/,
    ],
    attributes: ["class", "href", "src", "target"],
    styledTags: ["SPAN", "B", "STRONG", "I", "S", "U", "FONT", "TD"],
};

/**
 * @typedef {Object} ClipboardShared
 * @property {ClipboardPlugin['pasteText']} pasteText
 */

export class ClipboardPlugin extends Plugin {
    static id = "clipboard";
    static dependencies = [
        "dom",
        "selection",
        "sanitize",
        "history",
        "split",
        "delete",
        "lineBreak",
    ];
    static shared = ["pasteText"];

    setup() {
        this.addDomListener(this.editable, "copy", this.onCopy);
        this.addDomListener(this.editable, "cut", this.onCut);
        this.addDomListener(this.editable, "paste", this.onPaste);
        this.addDomListener(this.editable, "dragstart", this.onDragStart);
        this.addDomListener(this.editable, "drop", this.onDrop);
    }

    onCut(ev) {
        this.onCopy(ev);
        this.dependencies.history.stageSelection();
        this.dependencies.delete.deleteSelection();
        this.dependencies.history.addStep();
    }

    /**
     * @param {ClipboardEvent} ev
     */
    onCopy(ev) {
        ev.preventDefault();
        const selection = this.dependencies.selection.getEditableSelection();
        const commonAncestor = selection.commonAncestorContainer;
        if (commonAncestor && commonAncestor.nodeType === Node.ELEMENT_NODE) {
            this.dispatchTo("clean_handlers", commonAncestor);
        }
        let clonedContents = selection.cloneContents();
        if (!clonedContents.hasChildNodes()) {
            if (commonAncestor && commonAncestor.nodeType === Node.ELEMENT_NODE) {
                this.dispatchTo("normalize_handlers", commonAncestor);
            }
            return;
        }
        // Repair the copied range.
        if (clonedContents.firstChild.nodeName === "LI") {
            const list = selection.commonAncestorContainer.cloneNode();
            list.replaceChildren(...clonedContents.childNodes);
            clonedContents = list;
        }
        if (
            clonedContents.firstChild.nodeName === "TR" ||
            clonedContents.firstChild.nodeName === "TD"
        ) {
            // We enter this case only if selection is within single table.
            const table = closestElement(selection.commonAncestorContainer, "table");
            const tableClone = table.cloneNode(true);
            // A table is considered fully selected if it is nested inside a
            // cell that is itself selected, or if all its own cells are
            // selected.
            const isTableFullySelected =
                (table.parentElement &&
                    !!closestElement(table.parentElement, "td.o_selected_td")) ||
                [...table.querySelectorAll("td")]
                    .filter((td) => closestElement(td, "table") === table)
                    .every((td) => td.classList.contains("o_selected_td"));
            if (!isTableFullySelected) {
                for (const td of tableClone.querySelectorAll("td:not(.o_selected_td)")) {
                    if (closestElement(td, "table") === tableClone) {
                        // ignore nested
                        td.remove();
                    }
                }
                const trsWithoutTd = Array.from(tableClone.querySelectorAll("tr")).filter(
                    (row) => !row.querySelector("td")
                );
                for (const tr of trsWithoutTd) {
                    if (closestElement(tr, "table") === tableClone) {
                        // ignore nested
                        tr.remove();
                    }
                }
            }
            // If it is fully selected, clone the whole table rather than
            // just its rows.
            clonedContents = tableClone;
        }
        const startTable = closestElement(selection.startContainer, "table");
        if (clonedContents.firstChild.nodeName === "TABLE" && startTable) {
            // Make sure the full leading table is copied.
            clonedContents.firstChild.after(startTable.cloneNode(true));
            clonedContents.firstChild.remove();
        }
        const endTable = closestElement(selection.endContainer, "table");
        if (clonedContents.lastChild.nodeName === "TABLE" && endTable) {
            // Make sure the full trailing table is copied.
            clonedContents.lastChild.before(endTable.cloneNode(true));
            clonedContents.lastChild.remove();
        }
        const commonAncestorElement = closestElement(selection.commonAncestorContainer);
        if (commonAncestorElement && !isBlock(clonedContents.firstChild)) {
            // Get the list of ancestor elements starting from the provided
            // commonAncestorElement up to the block-level element.
            const blockEl = closestBlock(commonAncestorElement);
            const ancestorsList = [
                commonAncestorElement,
                ...ancestors(commonAncestorElement, blockEl),
            ];
            // Wrap rangeContent with clones of their ancestors to keep the styles.
            for (const ancestor of ancestorsList) {
                // Keep the formatting by keeping inline ancestors and paragraph
                // related ones like headings etc.
                if (!isBlock(ancestor) || paragraphRelatedElements.includes(ancestor.nodeName)) {
                    const clone = ancestor.cloneNode();
                    clone.append(...clonedContents.childNodes);
                    clonedContents.appendChild(clone);
                }
            }
        }
        const dataHtmlElement = this.document.createElement("data");
        dataHtmlElement.append(clonedContents);
        const odooHtml = dataHtmlElement.innerHTML;
        const odooText = selection.textContent();
        ev.clipboardData.setData("text/plain", odooText);
        ev.clipboardData.setData("text/html", odooHtml);
        ev.clipboardData.setData("application/vnd.odoo.odoo-editor", odooHtml);
        if (commonAncestor && commonAncestor.nodeType === Node.ELEMENT_NODE) {
            this.dispatchTo("normalize_handlers", commonAncestor);
        }
    }

    /**
     * Handle safe pasting of html or plain text into the editor.
     */
    onPaste(ev) {
        let selection = this.dependencies.selection.getEditableSelection();
        if (!selection.anchorNode.isConnected) {
            return;
        }
        // TODO ABD: TODO @phoenix: handle protected content
        // if (sel.anchorNode && (isProtected(sel.anchorNode) || isProtecting(sel.anchorNode))) {
        //     return;
        // }

        ev.preventDefault();

        this.dependencies.history.stageSelection();

        this.dispatchTo("before_paste_handlers", selection);
        // refresh selection after potential changes from `before_paste` handlers
        selection = this.dependencies.selection.getEditableSelection();

        this.handlePasteUnsupportedHtml(selection, ev.clipboardData) ||
            this.handlePasteOdooEditorHtml(ev.clipboardData) ||
            this.handlePasteHtml(selection, ev.clipboardData) ||
            this.handlePasteText(selection, ev.clipboardData);

        this.dependencies.history.addStep();
    }
    /**
     * @param {EditorSelection} selection
     * @param {DataTransfer} clipboardData
     */
    handlePasteUnsupportedHtml(selection, clipboardData) {
        const targetSupportsHtmlContent = isHtmlContentSupported(selection.anchorNode);
        if (!targetSupportsHtmlContent) {
            const text = clipboardData.getData("text/plain");
            this.dependencies.dom.insert(text);
            return true;
        }
    }
    /**
     * @param {DataTransfer} clipboardData
     */
    handlePasteOdooEditorHtml(clipboardData) {
        const odooEditorHtml = clipboardData.getData("application/vnd.odoo.odoo-editor");
        if (odooEditorHtml) {
            const fragment = parseHTML(this.document, odooEditorHtml);
            this.dependencies.sanitize.sanitize(fragment);
            if (fragment.hasChildNodes()) {
                this.dependencies.dom.insert(fragment);
            }
            return true;
        }
    }
    /**
     * @param {EditorSelection} selection
     * @param {DataTransfer} clipboardData
     */
    handlePasteHtml(selection, clipboardData) {
        const files = getImageFiles(clipboardData);
        const clipboardHtml = clipboardData.getData("text/html");
        if (files.length || clipboardHtml) {
            const clipboardElem = this.prepareClipboardData(clipboardHtml);
            // @phoenix @todo: should it be handled in table plugin?
            // When copy pasting a table from the outside, a picture of the
            // table can be included in the clipboard as an image file. In that
            // particular case the html table is given a higher priority than
            // the clipboard picture.
            if (files.length && !clipboardElem.querySelector("table")) {
                // @phoenix @todo: should it be handled in image plugin?
                return this.addImagesFiles(files).then((html) => {
                    this.dependencies.dom.insert(html);
                    this.dependencies.history.addStep();
                });
            } else {
                if (closestElement(selection.anchorNode, "a")) {
                    this.dependencies.dom.insert(clipboardElem.textContent);
                } else {
                    this.dependencies.dom.insert(clipboardElem);
                }
            }
            return true;
        }
    }
    /**
     * @param {EditorSelection} selection
     * @param {DataTransfer} clipboardData
     */
    handlePasteText(selection, clipboardData) {
        const text = clipboardData.getData("text/plain");
        if (this.delegateTo("paste_text_overrides", selection, text)) {
            return;
        } else {
            this.pasteText(selection, text);
        }
    }
    /**
     * @param {EditorSelection} selection
     * @param {string} text
     */
    pasteText(selection, text) {
        const textFragments = text.split(/\r?\n/);
        let textIndex = 1;
        for (const textFragment of textFragments) {
            // Replace consecutive spaces by alternating nbsp.
            const modifiedTextFragment = textFragment.replace(/( {2,})/g, (match) => {
                let alertnateValue = false;
                return match.replace(/ /g, () => {
                    alertnateValue = !alertnateValue;
                    const replaceContent = alertnateValue ? "\u00A0" : " ";
                    return replaceContent;
                });
            });
            this.dependencies.dom.insert(modifiedTextFragment);
            if (textIndex < textFragments.length) {
                // Break line by inserting new paragraph and
                // remove current paragraph's bottom margin.
                const p = closestElement(selection.anchorNode, "p");
                if (
                    this.dependencies.split.isUnsplittable(closestBlock(selection.anchorNode)) ||
                    closestElement(selection.anchorNode).tagName === "PRE"
                ) {
                    this.dependencies.lineBreak.insertLineBreak();
                } else {
                    const [pBefore] = this.dependencies.split.splitBlock();
                    if (p) {
                        pBefore.style.marginBottom = "0px";
                    }
                    selection = this.dependencies.selection.getEditableSelection();
                }
            }
            textIndex++;
        }
    }

    /**
     * Prepare clipboard data (text/html) for safe pasting into the editor.
     *
     * @private
     * @param {string} clipboardData
     * @returns {DocumentFragment}
     */
    prepareClipboardData(clipboardData) {
        const fragment = parseHTML(this.document, clipboardData);
        this.dependencies.sanitize.sanitize(fragment);
        const container = this.document.createElement("fake-container");
        container.append(fragment);

        for (const tableElement of container.querySelectorAll("table")) {
            tableElement.classList.add("table", "table-bordered", "o_table");
        }

        // todo: should it be in its own plugin ?
        const progId = container.querySelector('meta[name="ProgId"]');
        if (progId && progId.content === "Excel.Sheet") {
            // Microsoft Excel keeps table style in a <style> tag with custom
            // classes. The following lines parse that style and apply it to the
            // style attribute of <td> tags with matching classes.
            const xlStylesheet = container.querySelector("style");
            const xlNodes = container.querySelectorAll("[class*=xl],[class*=font]");
            for (const xlNode of xlNodes) {
                for (const xlClass of xlNode.classList) {
                    // Regex captures a CSS rule definition for that xlClass.
                    const xlStyle = xlStylesheet.textContent
                        .match(`.${xlClass}[^{]*{(?<xlStyle>[^}]*)}`)
                        .groups.xlStyle.replace("background:", "background-color:");
                    xlNode.setAttribute("style", xlNode.style.cssText + ";" + xlStyle);
                }
            }
        }
        for (const child of childNodes(container)) {
            this.cleanForPaste(child);
        }
        // Force inline nodes at the root of the container into separate P
        // elements. This is a tradeoff to ensure some features that rely on
        // nodes having a parent (e.g. convert to list, title, etc.) can work
        // properly on such nodes without having to actually handle that
        // particular case in all of those functions. In fact, this case cannot
        // happen on a new document created using this editor, but will happen
        // instantly when editing a document that was created from Etherpad.
        const result = this.document.createDocumentFragment();
        let p = this.document.createElement("p");
        for (const child of childNodes(container)) {
            if (isBlock(child)) {
                if (p.hasChildNodes()) {
                    result.appendChild(p);
                    p = this.document.createElement("p");
                }
                result.appendChild(child);
            } else {
                p.appendChild(child);
            }

            if (p.hasChildNodes()) {
                result.appendChild(p);
            }

            // Split elements containing <br> into seperate elements for each line.
            const brs = result.querySelectorAll("br");
            for (const br of brs) {
                const block = closestBlock(br);
                if (
                    ["P", "H1", "H2", "H3", "H4", "H5", "H6"].includes(block.nodeName) &&
                    !block.closest("li")
                ) {
                    // A linebreak at the beginning of a block is an empty line.
                    const isEmptyLine = block.firstChild.nodeName === "BR";
                    // Split blocks around it until only the BR remains in the
                    // block.
                    const remainingBrContainer = this.dependencies.split.splitAroundUntil(
                        br,
                        block
                    );
                    // Remove the container unless it represented an empty line.
                    if (!isEmptyLine) {
                        remainingBrContainer.remove();
                    }
                }
            }
        }
        return result;
    }
    /**
     * Clean a node for safely pasting. Cleaning an element involves unwrapping
     * its contents if it's an illegal (blacklisted or not whitelisted) element,
     * or removing its illegal attributes and classes.
     *
     * @param {Node} node
     */
    cleanForPaste(node) {
        if (
            !this.isWhitelisted(node) ||
            this.isBlacklisted(node) ||
            // Google Docs have their html inside a B tag with custom id.
            (node.id && node.id.startsWith("docs-internal-guid"))
        ) {
            if (!node.matches || node.matches(CLIPBOARD_BLACKLISTS.remove.join(","))) {
                node.remove();
            } else {
                let childNodes;
                if (node.nodeName === "DIV" && [...node.childNodes].every((n) => !isBlock(n))) {
                    // Convert <div> to <p> to preserve the inline structure
                    // while maintaining block-level behaviour.
                    const dir = node.getAttribute("dir");
                    const p = this.document.createElement("p");
                    if (dir) {
                        p.setAttribute("dir", dir);
                    }
                    p.append(...node.childNodes);
                    node.replaceWith(p);
                    childNodes = p.childNodes;
                } else {
                    // Unwrap the illegal node's contents.
                    childNodes = unwrapContents(node);
                }
                for (const child of childNodes) {
                    this.cleanForPaste(child);
                }
            }
        } else if (node.nodeType !== Node.TEXT_NODE) {
            if (node.nodeName === "TD") {
                if (node.hasAttribute("bgcolor") && !node.style["background-color"]) {
                    node.style["background-color"] = node.getAttribute("bgcolor");
                }
            } else if (node.nodeName === "FONT") {
                // FONT tags have some style information in custom attributes,
                // this maps them to the style attribute.
                if (node.hasAttribute("color") && !node.style["color"]) {
                    node.style["color"] = node.getAttribute("color");
                }
                if (node.hasAttribute("size") && !node.style["font-size"]) {
                    // FONT size uses non-standard numeric values.
                    node.style["font-size"] = +node.getAttribute("size") + 10 + "pt";
                }
            } else if (
                ["S", "U"].includes(node.nodeName) &&
                node.childNodes.length === 1 &&
                node.firstChild.nodeName === "FONT"
            ) {
                // S and U tags sometimes contain FONT tags. We prefer the
                // strike to adopt the style of the text, so we invert them.
                const fontNode = node.firstChild;
                node.before(fontNode);
                node.replaceChildren(...fontNode.childNodes);
                fontNode.appendChild(node);
            } else if (
                node.nodeName === "IMG" &&
                node.getAttribute("aria-roledescription") === "checkbox"
            ) {
                const checklist = node.closest("ul");
                const closestLi = node.closest("li");
                if (checklist) {
                    checklist.classList.add("o_checklist");
                    if (node.getAttribute("alt") === "checked") {
                        closestLi.classList.add("o_checked");
                    }
                    node.remove();
                    node = checklist;
                }
            }
            // Remove all illegal attributes and classes from the node, then
            // clean its children.
            for (const attribute of [...node.attributes]) {
                // Keep allowed styles on nodes with allowed tags.
                // todo: should the whitelist be a resource?
                if (
                    CLIPBOARD_WHITELISTS.styledTags.includes(node.nodeName) &&
                    attribute.name === "style"
                ) {
                    node.removeAttribute(attribute.name);
                    if (["SPAN", "FONT"].includes(node.tagName)) {
                        for (const unwrappedNode of unwrapContents(node)) {
                            this.cleanForPaste(unwrappedNode);
                        }
                    }
                } else if (!this.isWhitelisted(attribute)) {
                    node.removeAttribute(attribute.name);
                }
            }
            for (const klass of [...node.classList]) {
                if (!this.isWhitelisted(klass)) {
                    node.classList.remove(klass);
                }
            }
            for (const child of [...node.childNodes]) {
                this.cleanForPaste(child);
            }
        }
    }
    /**
     * Return true if the given attribute, class or node is whitelisted for
     * pasting, false otherwise.
     *
     * @private
     * @param {Attr | string | Node} item
     * @returns {boolean}
     */
    isWhitelisted(item) {
        if (item instanceof Attr) {
            return CLIPBOARD_WHITELISTS.attributes.includes(item.name);
        } else if (typeof item === "string") {
            return CLIPBOARD_WHITELISTS.classes.some((okClass) =>
                okClass instanceof RegExp ? okClass.test(item) : okClass === item
            );
        } else {
            return isTextNode(item) || item.matches?.(CLIPBOARD_WHITELISTS.nodes);
        }
    }
    /**
     * Return true if the given node is blacklisted for pasting, false
     * otherwise.
     *
     * @private
     * @param {Node} node
     * @returns {boolean}
     */
    isBlacklisted(node) {
        return (
            !isTextNode(node) &&
            node.matches([].concat(...Object.values(CLIPBOARD_BLACKLISTS)).join(","))
        );
    }

    /**
     * @param {DragEvent} ev
     */
    onDragStart(ev) {
        if (ev.target.nodeName === "IMG") {
            this.dragImage = ev.target instanceof HTMLElement && ev.target;
            ev.dataTransfer.setData(
                "application/vnd.odoo.odoo-editor-node",
                this.dragImage.outerHTML
            );
        }
    }
    /**
     * Handle safe dropping of html into the editor.
     *
     * @param {DragEvent} ev
     */
    async onDrop(ev) {
        ev.preventDefault();
        if (!isHtmlContentSupported(ev.target)) {
            return;
        }
        const dataTransfer = (ev.originalEvent || ev).dataTransfer;
        const imageNodeHTML = ev.dataTransfer.getData("application/vnd.odoo.odoo-editor-node");
        const image =
            imageNodeHTML &&
            this.dragImage &&
            imageNodeHTML === this.dragImage.outerHTML &&
            this.dragImage;

        const fileTransferItems = getImageFiles(dataTransfer);
        const htmlTransferItem = [...dataTransfer.items].find((item) => item.type === "text/html");
        if (image || fileTransferItems.length || htmlTransferItem) {
            if (this.document.caretPositionFromPoint) {
                const range = this.document.caretPositionFromPoint(ev.clientX, ev.clientY);
                this.dependencies.selection.setSelection({
                    anchorNode: range.offsetNode,
                    anchorOffset: range.offset,
                });
            } else if (this.document.caretRangeFromPoint) {
                const range = this.document.caretRangeFromPoint(ev.clientX, ev.clientY);
                this.dependencies.selection.setSelection({
                    anchorNode: range.startContainer,
                    anchorOffset: range.startOffset,
                });
            }
        }
        if (image) {
            const fragment = this.document.createDocumentFragment();
            fragment.append(image);
            this.dependencies.dom.insert(fragment);
            this.dependencies.history.addStep();
        } else if (fileTransferItems.length) {
            const html = await this.addImagesFiles(fileTransferItems);
            this.dependencies.dom.insert(html);
            this.dependencies.history.addStep();
        } else if (htmlTransferItem) {
            htmlTransferItem.getAsString((pastedText) => {
                this.dependencies.dom.insert(this.prepareClipboardData(pastedText));
                this.dependencies.history.addStep();
            });
        }
    }
    // @phoenix @todo: move to image or image paste plugin?
    /**
     * Add images inside the editable at the current selection.
     *
     * @param {File[]} imageFiles
     */
    async addImagesFiles(imageFiles) {
        const promises = [];
        for (const imageFile of imageFiles) {
            const imageNode = this.document.createElement("img");
            imageNode.classList.add("img-fluid");
            // Mark images as having to be saved as attachments.
            if (this.config.dropImageAsAttachment) {
                imageNode.classList.add("o_b64_image_to_save");
            }
            imageNode.dataset.fileName = imageFile.name;
            promises.push(
                getImageUrl(imageFile).then((url) => {
                    imageNode.src = url;
                    return imageNode;
                })
            );
        }
        const nodes = await Promise.all(promises);
        const fragment = this.document.createDocumentFragment();
        fragment.append(...nodes);
        return fragment;
    }
}

/**
 * @param {DataTransfer} dataTransfer
 */
function getImageFiles(dataTransfer) {
    return [...dataTransfer.items]
        .filter((item) => item.kind === "file" && item.type.includes("image/"))
        .map((item) => item.getAsFile());
}
/**
 * @param {File} file
 */
function getImageUrl(file) {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();

        reader.readAsDataURL(file);
        reader.onloadend = (e) => {
            if (reader.error) {
                return reject(reader.error);
            }
            resolve(e.target.result);
        };
    });
}

// @phoenix @todo: move to Odoo plugin?
/**
 * Returns true if the provided node can suport html content.
 *
 * @param {Node} node
 * @returns {boolean}
 */
export function isHtmlContentSupported(node) {
    return !closestElement(
        node,
        '[data-oe-model]:not([data-oe-field="arch"]):not([data-oe-type="html"]),[data-oe-translation-id]'
    );
}
