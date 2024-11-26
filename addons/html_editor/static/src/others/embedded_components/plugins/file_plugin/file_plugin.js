import { Plugin } from "@html_editor/plugin";
import { _t } from "@web/core/l10n/translation";
import { closestElement } from "@html_editor/utils/dom_traversal";
import { nextLeaf } from "@html_editor/utils/dom_info";
import { isBlock } from "@html_editor/utils/blocks";
import { renderFileCard } from "./utils";
import { FileDocumentsSelector } from "./file_documents_selector";
import { withSequence } from "@html_editor/utils/resource";

const fileMediaDialogTab = {
    id: "FILES",
    title: _t("Documents"),
    Component: FileDocumentsSelector,
    sequence: 15,
};

export class FilePlugin extends Plugin {
    static id = "file";
    static dependencies = ["embeddedComponents", "dom", "selection", "history"];
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
