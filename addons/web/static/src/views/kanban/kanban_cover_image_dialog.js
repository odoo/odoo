/** @odoo-module **/

import { Dialog } from "@web/core/dialog/dialog";
import { FileInput } from "@web/core/file_input/file_input";
import { useService } from "@web/core/utils/hooks";

import { Component, useState, onWillStart } from "@odoo/owl";

let nextDialogId = 1;

export class KanbanCoverImageDialog extends Component {
    setup() {
        this.id = `o_cover_image_upload_${nextDialogId++}`;
        this.orm = useService("orm");
        this.http = useService("http");
        const { record, fieldName } = this.props;
        const attachment = (record && record.data[fieldName]) || [];
        this.state = useState({
            selectFile: false,
            selectedAttachmentId: attachment[0],
        });
        onWillStart(async () => {
            this.attachments = await this.orm.searchRead(
                "ir.attachment",
                [
                    ["res_model", "=", record.resModel],
                    ["res_id", "=", record.resId],
                    ["mimetype", "ilike", "image"],
                ],
                ["id"]
            );
            this.state.selectFile = this.props.autoOpen && this.attachments.length;
        });
    }

    onUpload([attachment]) {
        if (!attachment) {
            return;
        }
        this.state.selectFile = false;
        this.selectAttachment(attachment, true);
    }

    selectAttachment(attachment, setSelected) {
        if (this.state.selectedAttachmentId !== attachment.id) {
            this.state.selectedAttachmentId = attachment.id;
        } else {
            this.state.selectedAttachmentId = null;
        }
        if (setSelected) {
            this.setCover();
        }
    }

    removeCover() {
        this.state.selectedAttachmentId = null;
        this.setCover();
    }

    async setCover() {
        const id = this.state.selectedAttachmentId ? [this.state.selectedAttachmentId] : false;
        await this.props.record.update({ [this.props.fieldName]: id });
        await this.props.record.save();
        this.props.close();
    }

    uploadImage() {
        this.state.selectFile = true;
    }
}

KanbanCoverImageDialog.template = "web.KanbanCoverImageDialog";
KanbanCoverImageDialog.components = { Dialog, FileInput };
