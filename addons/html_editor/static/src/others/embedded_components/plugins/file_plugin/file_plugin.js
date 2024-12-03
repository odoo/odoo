import { Plugin } from "@html_editor/plugin";
import { _t } from "@web/core/l10n/translation";
import { closestElement, selectElements } from "@html_editor/utils/dom_traversal";
import { isZwnbsp, nextLeaf } from "@html_editor/utils/dom_info";
import { isBlock } from "@html_editor/utils/blocks";
import { renderFileCard } from "./utils";
import { FileDocumentsSelector } from "./file_documents_selector";
import { withSequence } from "@html_editor/utils/resource";
import { isTextNode } from "@web/views/view_compiler";

/** @typedef {import("@html_editor/core/selection_plugin").Cursors} Cursors */

const fileMediaDialogTab = {
    id: "FILES",
    title: _t("Documents"),
    Component: FileDocumentsSelector,
    sequence: 15,
};

export class FilePlugin extends Plugin {
    static id = "file";
    static dependencies = ["embeddedComponents", "dom", "selection", "history", "feff"];
    resources = {
        user_commands: [
            {
                id: "uploadFile",
                title: _t("Upload a file"),
                description: _t("Add a download box"),
                icon: "fa-upload",
                run: this.uploadAndInsertFiles.bind(this),
                isAvailable: ({ anchorNode }) =>
                    !this.config.disableFile &&
                    !closestElement(anchorNode, "[data-embedded='clipboard']"),
            },
        ],
        powerbox_items: {
            categoryId: "media",
            commandId: "uploadFile",
            keywords: ["file"],
        },
        power_buttons: withSequence(5, { commandId: "uploadFile" }),
        mount_component_handlers: this.setupNewFile.bind(this),
        media_dialog_tabs_providers: () => (this.config.disableFile ? [] : [fileMediaDialogTab]),
        feff_providers: this.padFileCardsWithFeff.bind(this),
    };

    get recordInfo() {
        return this.config.getRecordInfo ? this.config.getRecordInfo() : {};
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
        const fileCards = attachments.map(renderFileCard);
        // Insert
        fileCards.forEach(this.dependencies.dom.insert);
        this.dependencies.history.addStep();
    }

    /**
     * Make sure that file elements have a ZWNBSP (\uFEFF) before and after them,
     * to allow the user to navigate around them with the keyboard.
     *
     * @param {Element} root
     * @param {Cursors} cursors
     */
    padFileCardsWithFeff(root, cursors) {
        return (
            [...selectElements(root, "[data-embedded='file']")]
                .flatMap((fileCard) => this.addFeffs(fileCard, cursors))
                // Avoid sequential FEFFs
                .filter((feff, i, array) => !(i > 0 && areCloseSiblings(array[i - 1], feff)))
        );
    }

    /**
     * @param {Element} element
     * @param {Cursors} cursors
     */
    addFeffs(element, cursors) {
        const addFeff = (position) => this.dependencies.feff.addFeff(element, position, cursors);
        return [
            isZwnbsp(element.previousSibling) ? element.previousSibling : addFeff("before"),
            isZwnbsp(element.nextSibling) ? element.nextSibling : addFeff("after"),
        ];
    }

    setupNewFile({ name, env }) {
        if (name === "file") {
            Object.assign(env, {
                editorShared: {
                    setSelectionAfter: (host) => {
                        try {
                            const leaf = nextLeaf(host, this.editable);
                            if (!leaf) {
                                return;
                            }
                            const leafEl = isBlock(leaf) ? leaf : leaf.parentElement;
                            if (isBlock(leafEl) && leafEl.isContentEditable) {
                                this.dependencies.selection.setSelection({
                                    anchorNode: leafEl,
                                    anchorOffset: 0,
                                });
                            }
                        } catch {
                            return;
                        }
                    },
                },
            });
        }
    }
}

/**
 * Whether two nodes are consecutive siblings, ignoring empty text nodes between
 * them.
 *
 * @param {Node} a
 * @param {Node} b
 */
function areCloseSiblings(a, b) {
    let next = a.nextSibling;
    // skip empty text nodes
    while (next && isTextNode(next) && !next.textContent) {
        next = next.nextSibling;
    }
    return next === b;
}
