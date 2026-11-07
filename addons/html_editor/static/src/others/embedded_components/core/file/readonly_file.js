import { _t } from "@web/core/l10n/translation";
import { downloadFile } from "@web/core/network/download";
import { useFileViewer } from "@web/core/file_viewer/file_viewer_hook";
import { useService } from "@web/core/utils/hooks";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import {
    EmbeddedComponentToolbar,
    EmbeddedComponentToolbarButton,
} from "@html_editor/others/embedded_components/core/embedded_component_toolbar/embedded_component_toolbar";
import { StateFileModel } from "@html_editor/others/embedded_components/core/file/state_file_model";
import { getEmbeddedProps } from "@html_editor/others/embedded_component_utils";
import { Component, onWillDestroy, proxy, t, useListener, useProps } from "@odoo/owl";
import { FileSettings } from "./file_settings";
import { useDropdownState } from "@web/core/dropdown/dropdown_hooks";

export class ReadonlyEmbeddedFileComponent extends Component {
    static components = {
        EmbeddedComponentToolbar,
        EmbeddedComponentToolbarButton,
        FileSettings,
    };
    props = useProps({
        fileData: t.object(),
        isPreviewInline: t.boolean().optional(false),
        host: t.object(),
    });
    static template = "html_editor.ReadonlyEmbeddedFile";

    setup() {
        this.dialogService = useService("dialog");
        this.state = proxy({
            fileData: { ...this.props.fileData },
            isPreviewInline: this.props.isPreviewInline,
        });
        this.fileModel = new StateFileModel(this.state);
        this.attachmentViewer = useFileViewer();

        this.hasSettingsOverlay = !!this.env.editorShared?.openFileSettings;
        this.dropdown = useDropdownState();
        useListener(this.props.host, "pointerenter", () => {
            if (this.isPreviewShown) {
                this.env.editorShared?.openFileSettings?.(this.props.host, {
                    isOverlay: true,
                    dropdown: this.dropdown,
                    fileModel: this.fileModel,
                    // Not reactive: the overlay props are read when it opens.
                    // This is fine since it only opens while the preview is
                    // shown, and toggling the preview closes it.
                    isPreviewInline: this.state.isPreviewInline,
                    download: this.download.bind(this),
                    rename: this.onFileRename?.bind(this),
                    toggleInlinePreview: this.toggleInlinePreview?.bind(this),
                    remove: this.onFileRemove?.bind(this),
                    host: this.props.host,
                });
            }
        });
        useListener(this.props.host, "pointerleave", (e) => {
            if (this.dropdown.isOpen || e.relatedTarget?.closest(".file-overlay")) {
                return;
            }
            this.closeSettingsOverlay();
        });

        onWillDestroy(() => this.closeSettingsOverlay());
    }

    closeSettingsOverlay() {
        this.env.editorShared?.closeFileSettings?.(this.props.host);
    }

    get isPreviewShown() {
        return this.state.isPreviewInline && this.fileModel.isViewable;
    }

    /**
     * This function will simply open a link that will trigger the download of
     * the associated file. If the url is not valid, the function will display
     * an error message.
     */
    async download() {
        try {
            await downloadFile(this.fileModel.downloadUrl);
        } catch {
            this.dialogService.add(AlertDialog, {
                body: _t(
                    "Oops, the file %s could not be found. Please replace this file box by a new one to re-upload the file.",
                    this.fileModel.name
                ),
                title: _t("Missing File"),
                confirm: () => {},
                confirmLabel: _t("Close"),
            });
        }
    }

    onClickFileImage() {
        if (this.fileModel.isViewable) {
            this.attachmentViewer.open(this.fileModel);
        } else {
            this.download();
        }
    }
}

export const readonlyFileEmbedding = {
    name: "file",
    Component: ReadonlyEmbeddedFileComponent,
    getProps: (host) => ({ host, ...getEmbeddedProps(host) }),
};
