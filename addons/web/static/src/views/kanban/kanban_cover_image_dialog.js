/** @odoo-module **/

import { SimpleDialog } from "@web/core/dialog/dialog";
import { useService } from "@web/core/utils/hooks";

const { Component, useState, useRef, onWillStart, onMounted } = owl;

let nextDialogId = 1;

export class KanbanCoverImageDialog extends Component {
    setup() {
        this.id = `o_cover_image_upload_${nextDialogId++}`;
        this.orm = useService("orm");
        const { record, fieldName } = this.props;
        this.coverId = record && record.data[fieldName];
        this.state = useState({
            selectedAttachmentId: this.coverId,
        });
        this.fileInput = useRef("fileInput");
        onWillStart(async () => {
            this.attachments = await this.orm.searchRead(
                "ir.attachment",
                [
                    ["res_model", "=", record.resModel],
                    ["res_id", "=", record.resId],
                    ["mimetype", "ilike", "image"],
                ],
                ["id", "name"]
            );
        });
        onMounted(() => {
            if (!this.props.autoOpen && this.attachments.length === 0) {
                this.fileInput.el.click();
            }
        });
    }

    selectAttachment(attachment) {
        if (this.state.selectedAttachmentId !== attachment.id) {
            this.state.selectedAttachmentId = attachment.id;
        } else {
            this.state.selectedAttachmentId = null;
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
}

KanbanCoverImageDialog.template = "web.KanbanCoverImageDialog";
KanbanCoverImageDialog.components = { SimpleDialog };
