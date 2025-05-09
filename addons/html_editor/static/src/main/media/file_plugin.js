import {
    DocumentSelector,
    renderStaticFileBox,
} from "@html_editor/main/media/media_dialog/document_selector";
import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { getActiveHotkey } from "@web/core/hotkeys/hotkey_service";
import { _t } from "@web/core/l10n/translation";
import { closestBlock } from "../../utils/blocks";
import { closestElement } from "../../utils/dom_traversal";
import { isTextNode } from "@html_editor/utils/dom_info";

export class FilePlugin extends Plugin {
    static id = "file";
    static dependencies = ["dom", "history", "selection"];
    resources = {
        user_commands: {
            id: "uploadFile",
            title: _t("Upload a file"),
            description: _t("Add a download box"),
            icon: "fa-upload",
            run: this.uploadAndInsertFiles.bind(this),
            isAvailable: this.isUploadCommandAvailable.bind(this),
        },
        powerbox_items: {
            categoryId: "media",
            commandId: "uploadFile",
            keywords: [_t("file"), _t("document")],
        },
        power_buttons: withSequence(5, { commandId: "uploadFile" }),
        unsplittable_node_predicates: (node) => node.classList?.contains("o_file_box"),
        ...(!this.config.disableFile && {
            media_dialog_extra_tabs: {
                id: "DOCUMENTS",
                title: _t("Documents"),
                Component: this.componentForMediaDialog,
                sequence: 15,
            },
        }),
        selectors_for_feff_providers: () => ".o_file_box",
    };

    setup() {
        this.addDomListener(this.editable, "keydown", (ev) => {
            if (["arrowup", "arrowdown"].includes(getActiveHotkey(ev))) {
                this.navigateFileBox(ev);
            }
        });
    }

    navigateFileBox(ev) {
        const isArrowUp = ev.key === "ArrowUp";
        const { anchorNode, anchorOffset } =
            this.dependencies.selection.getSelectionData().deepEditableSelection;

        const fileBox = closestElement(anchorNode, ".o_file_box");
        const baseNode = fileBox?.previousSibling || anchorNode;
        const block = closestBlock(baseNode);
        const currentNode = anchorNode === block ? block.childNodes[anchorOffset] : anchorNode;

        const findLineBreakNeighbor = (startNode = currentNode) => {
            let node = startNode;
            while (node && node.nodeName !== "BR") {
                node = isArrowUp ? node.previousSibling : node.nextSibling;
            }
            return isArrowUp ? node : node?.nextSibling;
        };

        const getNodeRect = (node, atCursor = true) => {
            if (!node) {
                return null;
            }

            if (node.nodeType === Node.TEXT_NODE) {
                if (atCursor) {
                    return this.document.getSelection().getRangeAt(0).getBoundingClientRect();
                }
                const range = this.document.createRange();
                range.selectNode(node);
                return range.getBoundingClientRect();
            }
            return node.getBoundingClientRect();
        };

        const currentRect = getNodeRect(currentNode);
        const nextLineNode = fileBox ? findLineBreakNeighbor(fileBox) : findLineBreakNeighbor();
        let targetRect;
        if (nextLineNode) {
            targetRect = getNodeRect(nextLineNode, false);
        } else {
            const siblingBlock = isArrowUp
                ? block.previousElementSibling
                : block.nextElementSibling;
            let nodeToTarget = isArrowUp ? siblingBlock?.lastChild : siblingBlock?.firstChild;
            if (nodeToTarget && isTextNode(nodeToTarget) && nodeToTarget.textContent === "\n") {
                nodeToTarget = isArrowUp ? nodeToTarget.previousSibling : nodeToTarget.nextSibling;
            }
            targetRect = getNodeRect(nodeToTarget, false);
        }

        if (targetRect) {
            const linkPopover = document.querySelector(".o-we-linkpopover");
            linkPopover?.classList.add("d-none");

            const x = currentRect.left;
            const y = targetRect.top;

            let targetNode, targetOffset;

            if (this.document.caretPositionFromPoint) {
                const pos = this.document.caretPositionFromPoint(x, y);
                targetNode = pos?.offsetNode;
                targetOffset = pos?.offset;
            } else if (this.document.caretRangeFromPoint) {
                const range = this.document.caretRangeFromPoint(x, y);
                targetNode = range?.startContainer;
                targetOffset = range?.startOffset;
            }

            linkPopover?.classList.remove("d-none");

            if (targetNode && targetOffset !== undefined) {
                const withinFileBoxScope = fileBox || closestElement(targetNode, ".o_file_box");
                if (withinFileBoxScope) {
                    ev.preventDefault();
                    this.dependencies.selection.setSelection({
                        anchorNode: targetNode,
                        anchorOffset: targetOffset,
                    });
                }
            }
        }
    }

    get recordInfo() {
        return this.config.getRecordInfo?.() || {};
    }

    isUploadCommandAvailable() {
        return !this.config.disableFile;
    }

    get componentForMediaDialog() {
        return DocumentSelector;
    }

    async uploadAndInsertFiles() {
        // Upload
        const attachments = await this.services.uploadLocalFiles.upload(this.recordInfo, {
            multiple: true,
            accessToken: true,
        });
        if (!attachments.length) {
            // No files selected or error during upload
            this.editable.focus();
            return;
        }
        if (this.config.onAttachmentChange) {
            attachments.forEach(this.config.onAttachmentChange);
        }
        // Render
        const fileCards = attachments.map(this.renderDownloadBox.bind(this));
        // Insert
        fileCards.forEach(this.dependencies.dom.insert);
        this.dependencies.history.addStep();
    }

    renderDownloadBox(attachment) {
        const url = this.services.uploadLocalFiles.getURL(attachment, {
            download: true,
            unique: true,
            accessToken: true,
        });
        const { name: filename, mimetype } = attachment;
        return renderStaticFileBox(filename, mimetype, url);
    }
}
