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
import { Component, useState } from "@odoo/owl";

export class ReadonlyEmbeddedFileComponent extends Component {
    static components = {
        EmbeddedComponentToolbar,
        EmbeddedComponentToolbarButton,
    };
    static props = {
        fileData: { type: Object },
        host: { type: Object },
    };
    static template = "html_editor.ReadonlyEmbeddedFile";

    setup() {
        this.dialogService = useService("dialog");
        this.state = useState({
            fileData: { ...this.props.fileData },
        });
        this.fileModel = new StateFileModel(this.state);
        this.attachmentViewer = useFileViewer();
    }

    /**
     * Callback function called when the user clicks on the "Download" button.
     * The function will simply open a link that will trigger the download of
     * the associated file. If the url is not valid, the function will display
     * an error message.
     * @param {Event} ev
     */
    async onClickDownload(ev) {
        ev.preventDefault();
        ev.stopPropagation();
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
        }
    }
}

export const readonlyFileEmbedding = {
    name: "file",
    Component: ReadonlyEmbeddedFileComponent,
    getProps: (host) => {
        return { host, ...getEmbeddedProps(host) };
    },
};
