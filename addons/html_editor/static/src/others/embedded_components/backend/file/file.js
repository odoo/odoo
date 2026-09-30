import { onWillDestroy, proxy, signal, useListener } from "@odoo/owl";
import { useDropdownState } from "@web/core/dropdown/dropdown_hooks";
import { useLayoutEffect } from "@web/owl2/utils";
import {
    applyObjectPropertyDifference,
    getEmbeddedProps,
    StateChangeManager,
    useEmbeddedState,
} from "@html_editor/others/embedded_component_utils";
import { ReadonlyEmbeddedFileComponent } from "@html_editor/others/embedded_components/core/file/readonly_file";
import { RenameDialog } from "./rename_dialog";

export class EmbeddedFileComponent extends ReadonlyEmbeddedFileComponent {
    static template = "html_editor.EmbeddedFile";

    nameInput = signal.ref();
    fileBox = signal.ref();

    setup() {
        super.setup();
        // override the state by an embedded state.
        this.state = useEmbeddedState(this.props.host);
        this.fileModel.state = this.state;
        this.localState = proxy({
            editFileName: false,
            boxWidth: 0,
        });
        useLayoutEffect(
            () => {
                if (this.localState.editFileName) {
                    const nameInput = this.nameInput();
                    nameInput?.focus();
                    nameInput?.select();
                }
            },
            () => [this.localState.editFileName]
        );

        this.hasSettingsOverlay = !!this.env.editorShared?.showFileSettingsOverlay;
        this.dropdown = useDropdownState();
        useListener(this.props.host, "pointerenter", () => {
            if (this.isPreviewShown) {
                this.env.editorShared?.showFileSettingsOverlay?.(this.props.host, {
                    isOverlay: true,
                    dropdown: this.dropdown,
                    fileModel: this.fileModel,
                    // Not reactive: the overlay props are read when it opens.
                    // This is fine since it only opens while the preview is
                    // shown, and toggling the preview closes it.
                    isPreviewInline: this.state.isPreviewInline,
                    download: this.download.bind(this),
                    rename: this.onFileRename.bind(this),
                    toggleInlinePreview: this.toggleInlinePreview.bind(this),
                    remove: this.onFileRemove.bind(this),
                    host: this.props.host,
                });
            }
        });
        useListener(this.props.host, "pointerleave", (e) => {
            if (this.dropdown.isOpen || e.relatedTarget?.closest(".file-overlay")) {
                return;
            }
            this.hideSettingsOverlay();
        });

        onWillDestroy(() => this.hideSettingsOverlay());
    }

    hideSettingsOverlay() {
        this.env.editorShared?.hideFileSettingsOverlay?.(this.props.host);
    }

    onBlurNameInput(ev) {
        this.localState.editFileName = false;
        this.renameFile(this.nameInput()?.value);
    }

    onFocusFileName(ev) {
        // The input replaces the file name: fix the file box width while
        // renaming, the input taking the space left by the file name.
        this.localState.boxWidth = this.fileBox()?.getBoundingClientRect().width || 0;
        this.localState.editFileName = true;
    }

    onKeydownNameInput(ev) {
        if (ev.key !== "Enter") {
            return;
        } else {
            ev.preventDefault();
        }
        if (this.renameFile(this.nameInput()?.value)) {
            this.localState.editFileName = false;
            this.env.editorShared?.setSelectionAfter(this.props.host);
        }
    }
    onFileRename() {
        if (!this.isPreviewShown) {
            // The file name is visible: edit it in place, as when clicking on
            // it.
            this.onFocusFileName();
            return;
        }
        // The preview replaces the file box: use a dialog.
        this.dialogService.add(RenameDialog, {
            filename: this.fileModel.filename,
            rename: this.renameFile.bind(this),
        });
    }
    onFileRemove() {
        this.env.editorShared?.remove(this.props.host);
    }
    toggleInlinePreview() {
        this.state.isPreviewInline = !this.state.isPreviewInline;
        this.env.editorShared?.setSelectionAfter(this.props.host);
        this.hideSettingsOverlay();
        // The preview is toggled from the settings dropdown, which takes the
        // focus out of the editable. Give it back, so that the HTML field
        // commits this change before the file name input can get the focus:
        // that commit restores the editable selection, which would blur it.
        this.env.editorShared?.focusEditable();
    }

    /**
     * @param {string} [newName]
     * @returns {boolean} whether the name is valid
     */
    renameFile(newName = "") {
        if (!newName.length) {
            return false;
        }
        if (newName === this.fileModel.filename) {
            return true;
        }
        // filename is the name of the file as written in the editor by the
        // user. It does not necessarily have the file extension.
        this.fileModel.filename = newName;
        if (this.fileModel.extension) {
            const pattern = new RegExp(`\\.${this.fileModel.extension}$`, "i");
            if (!newName.match(pattern)) {
                newName += `.${this.fileModel.extension}`;
            }
        }
        // name is the full name of the file (always with extension)
        // and is used as the url queryParam when downloading it.
        this.fileModel.name = newName;
        return true;
    }
}

export const fileEmbedding = {
    name: "file",
    Component: EmbeddedFileComponent,
    getProps: (host) => ({ host, ...getEmbeddedProps(host) }),
    getStateChangeManager: (config) =>
        new StateChangeManager(
            Object.assign(config, {
                propertyUpdater: {
                    fileData: (state, previous, next) => {
                        applyObjectPropertyDifference(
                            state,
                            "fileData",
                            previous.fileData,
                            next.fileData
                        );
                    },
                },
            })
        ),
};
