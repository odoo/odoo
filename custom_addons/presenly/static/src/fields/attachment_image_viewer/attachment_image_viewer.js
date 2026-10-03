import { Component } from "@odoo/owl";
import { FileModel } from "@web/core/file_viewer/file_model";
import { useFileViewer } from "@web/core/file_viewer/file_viewer_hook";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

export class PresenlyAttachmentImageViewer extends Component {
    static template = "presenly.AttachmentImageViewer";
    static props = { ...standardFieldProps };

    setup() {
        this.fileViewer = useFileViewer();
    }

    get attachment() {
        return this.props.record.data[this.props.name];
    }

    get thumbnailUrl() {
        return this.attachment ? `/web/image/${this.attachment.id}/240x240?unique=1` : false;
    }

    openViewer() {
        if (!this.attachment) {
            return;
        }
        const file = Object.assign(new FileModel(), {
            id: this.attachment.id,
            name: this.attachment.display_name || _t("Attendance Selfie"),
            mimetype: "image/jpeg",
            type: "binary",
            uploading: false,
        });
        this.fileViewer.open(file);
    }
}

export const presenlyAttachmentImageViewer = {
    component: PresenlyAttachmentImageViewer,
    displayName: _t("Attachment Image Viewer"),
    supportedTypes: ["many2one"],
};

registry.category("fields").add(
    "presenly_attachment_image_viewer",
    presenlyAttachmentImageViewer
);
