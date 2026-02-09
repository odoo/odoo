import {
    isTextNode,
    isParagraphRelatedElement,
    isEmptyBlock,
    isContentEditable,
} from "../utils/dom_info";
import { Plugin } from "../plugin";
import { closestBlock } from "../utils/blocks";
import { unwrapContents, wrapInlinesInBlocks, splitTextNode, fillEmpty } from "../utils/dom";
import { fillHtmlTransferData } from "../utils/clipboard";
import { childNodes, closestElement } from "../utils/dom_traversal";
import { parseHTML } from "../utils/html";
import {
    baseContainerGlobalSelector,
    getBaseContainerSelector,
} from "@html_editor/utils/base_container";
import { DIRECTIONS } from "../utils/position";
import { isHtmlContentSupported } from "./selection_plugin";

/**
 * @typedef { import("./selection_plugin").EditorSelection } EditorSelection
 *
 * @typedef {(() => boolean)[]} bypass_paste_image_files
 */

const CLIPBOARD_BLACKLISTS = {
    unwrap: [
        // These elements' children will be unwrapped.
        ".Apple-interchange-newline",
        "DIV", // DIV is unwrapped unless eligible to be a baseContainer, see cleanForPaste
    ],
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
        // Odoo tables
        "o_table",
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

const ONLY_LINK_REGEX = /^(https?:\/\/)?([\w-]+\.)+[\w-]+(\/[\w-./?%&=]*)?$/i;

/**
 * @typedef {Object} ClipboardShared
 * @property {ClipboardPlugin['pasteText']} pasteText
 */

/**
 * @typedef {((img: HTMLImageElement) => void)[]} added_image_handlers
 * @typedef {(() => void)[]} after_paste_handlers
 * @typedef {(() => void)[]} before_paste_handlers
 *
 * @typedef {((selection: EditorSelection, text: string) => boolean)[]} paste_text_overrides
 *
 * @typedef {((
 *     clonedContents: DocumentFragment,
 *     selection: EditorSelection
 *   ) => void | clonedContents)[]} clipboard_content_processors
 * @typedef {((textContent: string) => string)[]} clipboard_text_processors
 */

export class ClipboardPlugin extends Plugin {
    static id = "clipboard";
    static dependencies = [
        "baseContainer",
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
        const selection = this.dependencies.selection.getEditableSelection();
        this.dispatchTo("before_cut_handlers", selection);
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
        this.setSelectionTransferData(ev, "clipboardData");
    }

    /**
     * Prepare HTML and plain text from the current selection.
     */
    setSelectionTransferData(ev, transferObjectProperty) {
        const selection = this.dependencies.selection.getEditableSelection();
        let clonedContents = selection.cloneContents();
        if (!clonedContents.hasChildNodes()) {
            return;
        }
        // Prepare text content for clipboard.
        let textContent = selection.textContent();
        for (const processor of this.getResource("clipboard_text_processors")) {
            textContent = processor(textContent);
        }

        // Prepare html content for clipboard.
        for (const processor of this.getResource("clipboard_content_processors")) {
            clonedContents = processor(clonedContents, selection) || clonedContents;
        }
        this.dependencies.dom.removeSystemProperties(clonedContents);
        fillHtmlTransferData(ev, transferObjectProperty, clonedContents, {
            setEditorTransferData:
                isContentEditable(selection.commonAncestorContainer) ||
                this.dependencies.selection.isNodeEditable(selection.commonAncestorContainer),
            textContent,
        });
    }

    /**
     * Handle safe pasting of html or plain text into the editor.
     */
    onPaste(ev) {
        let selection = this.dependencies.selection.getEditableSelection();
        if (
            !selection.anchorNode.isConnected ||
            !closestElement(selection.anchorNode).isContentEditable
        ) {
            return;
        }
        ev.preventDefault();

        this.dependencies.history.stageSelection();

        this.dispatchTo("before_paste_handlers", selection, ev);
        // refresh selection after potential changes from `before_paste` handlers
        selection = this.dependencies.selection.getEditableSelection();

        this.handlePasteUnsupportedHtml(selection, ev.clipboardData) ||
            this.handlePasteOdooEditorHtml(ev.clipboardData) ||
            this.handlePasteHtml(selection, ev.clipboardData) ||
            this.handlePasteText(selection, ev.clipboardData);

        this.dispatchTo("after_paste_handlers", selection);
        this.dependencies.history.addStep();
    }
    /**
     * @param {EditorSelection} selection
     * @param {DataTransfer} clipboardData
     */
    handlePasteUnsupportedHtml(selection, clipboardData) {
        if (!isHtmlContentSupported(selection)) {
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
        const textContent = clipboardData.getData("text/plain");
        if (ONLY_LINK_REGEX.test(textContent)) {
            return false;
        }
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
        const files = this.delegateTo("bypass_paste_image_files")
            ? []
            : getImageFiles(clipboardData);
        const clipboardHtml = clipboardData.getData("text/html");
        const textContent = clipboardData.getData("text/plain");
        if (ONLY_LINK_REGEX.test(textContent)) {
            return false;
        }
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
            } else if (clipboardElem.hasChildNodes()) {
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
            this.pasteText(text);
        }
    }
    /**
     * @param {string} text
     */
    pasteText(text) {
        const textFragments = text.split(/\r?\n/);
        let selection = this.dependencies.selection.getEditableSelection();
        const preEl = closestElement(selection.anchorNode, "PRE");
        let textIndex = 1;
        for (const textFragment of textFragments) {
            let modifiedTextFragment = textFragment;

            // <pre> preserves whitespace by default, so no need for &nbsp.
            if (!preEl) {
                // Replace consecutive spaces by alternating nbsp.
                modifiedTextFragment = textFragment.replace(/( {2,})/g, (match) => {
                    let alternateValue = false;
                    return match.replace(/ /g, () => {
                        alternateValue = !alternateValue;
                        const replaceContent = alternateValue ? "\u00A0" : " ";
                        return replaceContent;
                    });
                });
            }
            this.dependencies.dom.insert(modifiedTextFragment);
            if (textIndex < textFragments.length) {
                selection = this.dependencies.selection.getEditableSelection();
                // Break line by inserting new paragraph and
                // remove current paragraph's bottom margin.
                const block = closestBlock(selection.anchorNode);
                if (
                    this.dependencies.split.isUnsplittable(block) ||
                    closestElement(selection.anchorNode).tagName === "PRE"
                ) {
                    this.dependencies.lineBreak.insertLineBreak();
                } else {
                    const [blockBefore] = this.dependencies.split.splitBlock();
                    if (
                        block &&
                        block.matches(baseContainerGlobalSelector) &&
                        blockBefore &&
                        !blockBefore.matches(getBaseContainerSelector("DIV"))
                    ) {
                        // Do something only if blockBefore is not a DIV (which is the no-margin option)
                        // replace blockBefore by a DIV.
                        const div = this.dependencies.baseContainer.createBaseContainer("DIV");
                        const cursors = this.dependencies.selection.preserveSelection();
                        blockBefore.before(div);
                        div.replaceChildren(...childNodes(blockBefore));
                        blockBefore.remove();
                        cursors.remapNode(blockBefore, div).restore();
                    }
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
        if (this.delegateTo("bypass_paste_image_files")) {
            for (const imgElement of container.querySelectorAll("img")) {
                imgElement.remove();
            }
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
        const childContent = childNodes(container);
        for (const child of childContent) {
            this.cleanForPaste(child);
        }
        // Identify the closest baseContainer from the selection. This will
        // determine which baseContainer will be used by default for the
        // clipboard content if it has to be modified.
        const selection = this.dependencies.selection.getEditableSelection();
        const closestBaseContainer =
            selection.anchorNode &&
            closestElement(selection.anchorNode, baseContainerGlobalSelector);
        // Force inline nodes at the root of the container into separate `baseContainers`
        // elements. This is a tradeoff to ensure some features that rely on
        // nodes having a parent (e.g. convert to list, title, etc.) can work
        // properly on such nodes without having to actually handle that
        // particular case in all of those functions. In fact, this case cannot
        // happen on a new document created using this editor, but will happen
        // instantly when editing a document that was created from Etherpad.
        wrapInlinesInBlocks(container, {
            baseContainerNodeName:
                closestBaseContainer?.nodeName ||
                this.dependencies.baseContainer.getDefaultNodeName(),
        });
        const result = this.document.createDocumentFragment();
        result.replaceChildren(...childNodes(container));

        // Split elements containing <br> into separate elements for each line.
        const brs = result.querySelectorAll("br");
        for (const br of brs) {
            const block = closestBlock(br);
            if (
                (isParagraphRelatedElement(block) ||
                    this.dependencies.baseContainer.isCandidateForBaseContainer(block)) &&
                block.nodeName !== "PRE"
            ) {
                // A linebreak at the beginning of a block is an empty line.
                const isEmptyLine = block.firstChild.nodeName === "BR";
                // Split blocks around it until only the BR remains in the
                // block.
                const remainingBrContainer = this.dependencies.split.splitAroundUntil(br, block);
                // Remove the container unless it represented an empty line.
                if (!isEmptyLine) {
                    remainingBrContainer.remove();
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
                let childrenNodes;
                if (node.nodeName === "DIV") {
                    if (!node.hasChildNodes()) {
                        node.remove();
                        return;
                    } else if (this.dependencies.baseContainer.isCandidateForBaseContainer(node)) {
                        const whiteSpace = node.style?.whiteSpace;
                        if (whiteSpace && !["normal", "nowrap"].includes(whiteSpace)) {
                            node.innerHTML = node.innerHTML.replace(/\n/g, "<br>");
                        }
                        const baseContainer = this.dependencies.baseContainer.createBaseContainer();
                        const dir = node.getAttribute("dir");
                        if (dir) {
                            baseContainer.setAttribute("dir", dir);
                        }
                        baseContainer.append(...node.childNodes);

                        node.replaceWith(baseContainer);
                        childrenNodes = childNodes(baseContainer);
                    } else {
                        childrenNodes = unwrapContents(node);
                    }
                } else {
                    // Unwrap the illegal node's contents.
                    childrenNodes = unwrapContents(node);
                }
                for (const child of childrenNodes) {
                    this.cleanForPaste(child);
                }
            }
        } else if (node.nodeType !== Node.TEXT_NODE) {
            if (node.nodeName === "THEAD") {
                const tbody = node.nextElementSibling;
                if (tbody) {
                    // If a <tbody> already exists, move all rows from
                    // <thead> into the start of <tbody>.
                    tbody.prepend(...node.children);
                    node.remove();
                    node = tbody;
                } else {
                    // Otherwise, replace the <thead> with <tbody>
                    node = this.dependencies.dom.setTagName(node, "TBODY");
                }
            } else if (["TD", "TH"].includes(node.nodeName)) {
                // Insert base container into empty TD.
                if (isEmptyBlock(node)) {
                    const baseContainer = this.dependencies.baseContainer.createBaseContainer();
                    fillEmpty(baseContainer);
                    node.replaceChildren(baseContainer);
                }

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
                childNodes(node).length === 1 &&
                node.firstChild.nodeName === "FONT"
            ) {
                // S and U tags sometimes contain FONT tags. We prefer the
                // strike to adopt the style of the text, so we invert them.
                const fontNode = node.firstChild;
                node.before(fontNode);
                node.replaceChildren(...childNodes(fontNode));
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
            for (const child of childNodes(node)) {
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
        if (item.nodeType === Node.ATTRIBUTE_NODE) {
            return CLIPBOARD_WHITELISTS.attributes.includes(item.name);
        } else if (typeof item === "string") {
            return CLIPBOARD_WHITELISTS.classes.some((okClass) =>
                okClass instanceof RegExp ? okClass.test(item) : okClass === item
            );
        } else {
            return isTextNode(item) || item.matches?.(CLIPBOARD_WHITELISTS.nodes.join(","));
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
        const selection = this.dependencies.selection.getEditableSelection();
        this.dispatchTo("before_drag_handlers", selection);
        this.setSelectionTransferData(ev, "dataTransfer");
    }
    /**
     * Handle safe dropping of html into the editor.
     *
     * @param {DragEvent} ev
     */
    async onDrop(ev) {
        ev.preventDefault();
        const selection = this.dependencies.selection.getEditableSelection();
        if (!isHtmlContentSupported(selection)) {
            return;
        }
        const nodeToSplit =
            selection.direction === DIRECTIONS.RIGHT ? selection.focusNode : selection.anchorNode;
        const offsetToSplit =
            selection.direction === DIRECTIONS.RIGHT
                ? selection.focusOffset
                : selection.anchorOffset;
        if (nodeToSplit.nodeType === Node.TEXT_NODE && !selection.isCollapsed) {
            const selectionToRestore = this.dependencies.selection.preserveSelection();
            // Split the text node beforehand to ensure the insertion offset
            // remains correct after deleting the selection.
            splitTextNode(nodeToSplit, offsetToSplit, DIRECTIONS.LEFT);
            selectionToRestore.restore();
        }

        const dataTransfer = (ev.originalEvent || ev).dataTransfer;
        const odooEditorHtml = ev.dataTransfer.getData("application/vnd.odoo.odoo-editor");
        const fileTransferItems = !odooEditorHtml && getImageFiles(dataTransfer);
        const htmlTransferItem = [...dataTransfer.items].find((item) => item.type === "text/html");
        if (fileTransferItems.length || htmlTransferItem || odooEditorHtml) {
            const deleteAndSetSelection = (offsetNode, offset) => {
                if (offsetNode.nodeType === Node.ELEMENT_NODE && offset > 1) {
                    // Store number of children before deleting selection
                    // Deleting the selection may remove one or more child nodes,
                    // which shifts the indices of remaining children. To keep the
                    // caret at the intended position, we subtract the number of
                    // removed children from the original offset.
                    const initialLength = offsetNode.childNodes.length;
                    this.dependencies.delete.deleteSelection();
                    const removedCount = initialLength - offsetNode.childNodes.length;
                    offset -= removedCount;
                } else {
                    // For TEXT_NODEs, offset remains valid; just delete selection
                    this.dependencies.delete.deleteSelection();
                }

                this.dependencies.selection.setSelection({
                    anchorNode: offsetNode,
                    anchorOffset: offset,
                });
            };

            if (this.document.caretPositionFromPoint) {
                const range = this.document.caretPositionFromPoint(ev.clientX, ev.clientY);
                deleteAndSetSelection(range.offsetNode, range.offset);
            } else if (this.document.caretRangeFromPoint) {
                const range = this.document.caretRangeFromPoint(ev.clientX, ev.clientY);
                deleteAndSetSelection(range.startContainer, range.startOffset);
            }
        }
        if (odooEditorHtml) {
            const fragment = parseHTML(this.document, odooEditorHtml);
            this.dependencies.sanitize.sanitize(fragment);
            if (fragment.hasChildNodes()) {
                this.dependencies.dom.insert(fragment);
                this.dependencies.history.addStep();
            }
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
            this.dispatchTo("added_image_handlers", imageNode);
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
