/** @odoo-module native */
import {
    DocumentSelector,
    renderStaticFileBox,
} from "@html_editor/main/media/media_dialog/document_selector";
import { Plugin } from "@html_editor/plugin";
import { closestElement, firstLeaf, lastLeaf } from "@html_editor/utils/dom_traversal";
import { nodeSize } from "@html_editor/utils/position";
import { withSequence } from "@html_editor/utils/resource";
import { _t } from "@web/core/translation";

import { DISABLED_NAMESPACE } from "../toolbar/toolbar_plugin.js";
import { isLinkSupported } from "../link/link_plugin.js";

export class FilePlugin extends Plugin {
    static id = "file";
    static dependencies = ["clipboard", "dom", "history", "selection"];
    static defaultConfig = {
        allowFile: true,
    };
    /** @type {import("plugins").EditorResources} */
    resources = {
        user_commands: {
            id: "uploadFile",
            title: _t("Upload a file"),
            description: _t("Add a download box"),
            icon: "fa-upload",
            run: this.uploadAndInsertFiles.bind(this),
            isAvailable: (selection) =>
                this.isUploadCommandAvailable(selection) && isLinkSupported(selection),
        },
        powerbox_items: {
            categoryId: "media",
            commandId: "uploadFile",
            keywords: [_t("file"), _t("document")],
        },
        power_buttons: withSequence(5, {
            commandId: "uploadFile",
            description: _t("Upload a file"),
        }),
        unsplittable_node_predicates: (node) => node.classList?.contains("o_file_box"),
        ...(this.config.allowFile &&
            this.config.allowMediaDocuments && {
                media_dialog_extra_tabs: {
                    id: "DOCUMENTS",
                    title: _t("Documents"),
                    Component: this.componentForMediaDialog,
                    sequence: 15,
                },
            }),
        selectors_for_feff_providers: () => ".o_file_box",
        toolbar_namespace_providers: withSequence(
            80,
            (targetedNodes, editableSelection) =>
                closestElement(editableSelection.anchorNode, ".o_file_box") &&
                DISABLED_NAMESPACE,
        ),

        functional_empty_node_predicates: (node) =>
            node?.nodeName === "SPAN" && node.classList.contains("o_file_box"),
        is_node_editable_predicates: (node) => {
            if (node?.nodeName === "SPAN" && node.classList.contains("o_file_box")) {
                return false;
            }
        },

        paste_overrides: (selection, clipboardData) => {
            if (closestElement(selection.anchorNode, ".o_file_box")) {
                this.dependencies.clipboard.pasteText(
                    clipboardData.getData("text/plain"),
                );
                return true;
            }
        },
    };

    setup() {
        this.editable.addEventListener("click", this.onClick.bind(this));
        this.editable.addEventListener("keydown", this.onKeyDown.bind(this));
        this.document.addEventListener("pointerdown", this.onPointerDown.bind(this));
    }

    onClick(ev) {
        const fileNameEl = closestElement(
            ev.target,
            ".o_file_name_container .o_link_readonly",
        );
        if (!fileNameEl || fileNameEl.isContentEditable) {
            return;
        }
        ev.preventDefault();
        ev.stopPropagation();
        fileNameEl.setAttribute("contenteditable", "true");

        let anchorNode, anchorOffset;
        if (this.document.caretPositionFromPoint) {
            const pos = this.document.caretPositionFromPoint(ev.clientX, ev.clientY);
            anchorNode = pos?.offsetNode;
            anchorOffset = pos?.offset;
        } else if (this.document.caretRangeFromPoint) {
            const range = document.caretRangeFromPoint(ev.clientX, ev.clientY);
            anchorNode = range?.startContainer;
            anchorOffset = range?.startOffset;
        }

        if (anchorNode && fileNameEl.contains(anchorNode)) {
            this.dependencies.selection.setSelection({ anchorNode, anchorOffset });
        } else {
            this.dependencies.selection.setCursorStart(fileNameEl);
        }
    }

    onKeyDown(ev) {
        const fileNameEl = closestElement(
            ev.target,
            ".o_file_name_container .o_link_readonly",
        );
        if (!fileNameEl) {
            return;
        }
        const selection = this.dependencies.selection.getEditableSelection();
        const firstLeafNode = firstLeaf(fileNameEl);
        const lastLeafNode = lastLeaf(fileNameEl);
        switch (ev.key) {
            case "ArrowLeft":
                if (
                    selection.isCollapsed &&
                    selection.anchorNode === firstLeafNode &&
                    selection.anchorOffset === 0
                ) {
                    ev.preventDefault();
                }
                break;
            case "ArrowRight":
                if (
                    selection.isCollapsed &&
                    selection.anchorNode === lastLeafNode &&
                    selection.anchorOffset === nodeSize(lastLeafNode)
                ) {
                    ev.preventDefault();
                }
                break;
            case "ArrowUp":
                ev.preventDefault();
                this.dependencies.selection.setCursorStart(fileNameEl);
                break;
            case "ArrowDown":
                ev.preventDefault();
                this.dependencies.selection.setCursorEnd(fileNameEl);
                break;
            case "Enter":
                ev.preventDefault();
                break;
        }
    }

    onPointerDown(ev) {
        const activeElement = this.document.activeElement;
        const fileNameEl = closestElement(
            activeElement,
            ".o_file_name_container .o_link_readonly",
        );
        if (!fileNameEl || fileNameEl.contains(ev.target)) {
            return;
        }
        activeElement.setAttribute("contenteditable", "false");
    }

    get recordInfo() {
        return this.config.getRecordInfo?.() || {};
    }

    isUploadCommandAvailable() {
        return this.config.allowFile;
    }

    get componentForMediaDialog() {
        return DocumentSelector;
    }

    async uploadAndInsertFiles() {
        const uploadParams = this.config.publicAttachments
            ? {}
            : { ...this.recordInfo };
        const attachments = await this.services.uploadLocalFiles.upload(uploadParams, {
            multiple: true,
            accessToken: true,
        });
        if (!attachments.length) {
            this.editable.focus();
            return;
        }
        if (this.config.onAttachmentChange) {
            attachments.forEach(this.config.onAttachmentChange);
        }
        const fileCards = attachments.map(this.renderDownloadBox.bind(this));
        fileCards.forEach(this.dependencies.dom.insert);
        this.dependencies.history.addStep();
    }

    renderDownloadBox(attachment) {
        const url = this.services.uploadLocalFiles.getURL(attachment, {
            download: true,
            unique: true,
            accessToken: true,
        });
        const { name: filename, mimetype, id } = attachment;
        return renderStaticFileBox(filename, mimetype, url, id);
    }
}
