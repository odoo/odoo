import { nextLeaf } from "@html_editor/utils/dom_info";
import { isBlock } from "@html_editor/utils/blocks";
import { EmbeddedFileDocumentsSelector, renderFileCard } from "./embedded_file_documents_selector";
import { FilePlugin } from "@html_editor/main/media/file_plugin";
import { closestElement } from "@html_editor/utils/dom_traversal";

/**
 * This plugin is meant to replace the File plugin.
 */
export class EmbeddedFilePlugin extends FilePlugin {
    static id = "embeddedFile";
    static dependencies = [...super.dependencies, "embeddedComponents", "selection"];

    constructor(...args) {
        super(...args);
        // Extend resources
        this.resources = {
            ...this.resources,
            mount_component_handlers: this.setupNewFile.bind(this),
            selectors_for_feff_providers: () => "[data-embedded='file']",
        };
    }

    /** @override */
    renderDownloadBox(attachment) {
        return renderFileCard(attachment);
    }

    /** @override */
    isUploadCommandAvailable({ anchorNode }) {
        return (
            super.isUploadCommandAvailable() &&
            !closestElement(anchorNode, "[data-embedded='clipboard']")
        );
    }

    /** @override */
    get componentForMediaDialog() {
        return EmbeddedFileDocumentsSelector;
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
