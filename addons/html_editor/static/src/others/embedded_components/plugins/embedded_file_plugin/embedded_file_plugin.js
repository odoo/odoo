import { nextLeaf } from "@html_editor/utils/dom_info";
import { isBlock } from "@html_editor/utils/blocks";
import {
    EmbeddedFileDocumentsSelector,
    renderEmbeddedFileBox,
} from "./embedded_file_documents_selector";
import { FilePlugin } from "@html_editor/main/media/file_plugin";
import { closestElement } from "@html_editor/utils/dom_traversal";

/**
 * This plugin is meant to replace the File plugin.
 */
export class EmbeddedFilePlugin extends FilePlugin {
    static id = "embeddedFile";
    static dependencies = [
        ...super.dependencies,
        "delete",
        "embeddedComponents",
        "overlay",
        "selection",
    ];

    // Extends the base class resources
    /** @type {import("plugins").EditorResources} */
    resources = {
        ...this.resources,
        on_will_mount_component_handlers: this.setupNewFile.bind(this),
    };

    /** @override */
    renderDownloadBox(attachment) {
        return renderEmbeddedFileBox(attachment, this.document);
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
            Object.assign(env.editorShared, {
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
                remove: (host) => {
                    const cursor = this.dependencies.selection.preserveSelection();
                    const index = [...host.parentElement.childNodes].indexOf(host);
                    this.dependencies.selection.setSelection({
                        anchorNode: host.parentElement,
                        anchorOffset: index + 1,
                    });
                    this.dependencies.delete.delete("backward", "character");
                    cursor.restore();
                },
                createOverlay: this.dependencies.overlay.createOverlay,
                focusEditable: this.dependencies.selection.focusEditable,
            });
        }
    }
}
