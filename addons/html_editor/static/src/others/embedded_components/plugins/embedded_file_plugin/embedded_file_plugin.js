import { nextLeaf } from "@html_editor/utils/dom_info";
import { isBlock } from "@html_editor/utils/blocks";
import {
    EmbeddedFileDocumentsSelector,
    renderEmbeddedFileBox,
} from "./embedded_file_documents_selector";
import { FilePlugin } from "@html_editor/main/media/file_plugin";
import { closestElement } from "@html_editor/utils/dom_traversal";
import { FileSettings } from "@html_editor/others/embedded_components/core/file/file_settings";

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
    setup() {
        super.setup();
        // A single settings overlay is shared by all the file components.
        this.fileSettingsOverlay = this.dependencies.overlay.createOverlay(FileSettings, {
            positionOptions: {
                position: "right-start",
            },
            className: "file-overlay",
            closeOnPointerdown: false,
        });
        this.fileSettingsHost = null;
    }

    showFileSettingsOverlay(host, props) {
        if (this.fileSettingsHost !== host) {
            this.fileSettingsOverlay.close();
            this.fileSettingsHost = host;
        }
        this.fileSettingsOverlay.open({
            target: host,
            props: { ...props, hideOverlay: () => this.hideFileSettingsOverlay(host) },
        });
    }

    hideFileSettingsOverlay(host) {
        if (this.fileSettingsHost === host) {
            this.fileSettingsOverlay.close();
            this.fileSettingsHost = null;
        }
    }

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
                    const parent = host.parentElement;
                    const index = [...parent.childNodes].indexOf(host);
                    this.dependencies.delete.deleteRange({
                        startContainer: parent,
                        startOffset: index,
                        endContainer: parent,
                        endOffset: index + 1,
                    });
                    cursor.restore();
                    this.dependencies.history.commit();
                    this.dependencies.selection.focusEditable();
                },
                showFileSettingsOverlay: this.showFileSettingsOverlay.bind(this),
                hideFileSettingsOverlay: this.hideFileSettingsOverlay.bind(this),
                focusEditable: this.dependencies.selection.focusEditable,
            });
        }
    }
}
