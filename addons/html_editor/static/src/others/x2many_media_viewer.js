import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { X2ManyField, x2ManyField } from "@web/views/fields/x2many/x2many_field";
import { getVideoUrl } from "../utils/url";
import { useChildSubEnv } from "@odoo/owl";
import { CustomMediaDialog } from "./custom_media_dialog";

export class X2ManyMediaViewer extends X2ManyField {
    static template = "html_editor.X2ManyMediaViewer";

    setup() {
        super.setup();
        this.dialogs = useService("dialog");
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.supportedFields = ["image_1920", "image_1024", "image_512", "image_256", "image_128"];
        useChildSubEnv({
            parentField: this.props.name,
        });
    }

    addMedia() {
        this.dialogs.add(CustomMediaDialog, {
            save: (el) => {}, // Simple rebound to fake its execution
            multiImages: true,
            noDocuments: true,
            noIcons: true,
            imageSave: this.onImageSave.bind(this),
            videoSave: this.onVideoSave.bind(this),
        });
    }

    onVideoSave(videoInfo) {
        const url = getVideoUrl(videoInfo[0].platform, videoInfo[0].videoId, videoInfo[0].params);
        const videoList = this.props.record.data[this.props.name];
        videoList.addNewRecord({ position: "bottom" }).then((record) => {
            record.update({ name: videoInfo[0].platform + " - [Video]", video_url: url.href });
        });
    }

    async onImageSave(attachments) {
        const attachmentIds = attachments.map((attachment) => attachment.id);
        const attachmentRecords = await this.orm.searchRead(
            "ir.attachment",
            [["id", "in", attachmentIds]],
            ["id", "datas", "name"],
            {}
        );
        attachmentRecords.forEach((attachment) => {
            const imageList = this.props.record.data[this.props.name];
            if (!attachment.datas) {
                // URL type attachments are mostly demo records which don't have any ir.attachment datas
                // TODO: make it work with URL type attachments
                return this.notification.add(`Cannot add URL type attachment "${attachment.name}". Please try to reupload this image.`, {
                    type: "warning",
                });
            }
            imageList.addNewRecord({ position: "bottom" }).then((record) => {
                const activeFields = imageList.activeFields;
                const updateData = {};
                for (const field in activeFields) {
                    if (attachment.datas && this.supportedFields.includes(field)) {
                        updateData[field] = attachment.datas;
                        updateData["name"] = attachment.name;
                    }
                }
                record.update(updateData);
            });
        });
    }

    async onAdd({ context, editable } = {}) {
        this.addMedia();
    }
}

export const x2ManyMediaViewer = {
    ...x2ManyField,
    component: X2ManyMediaViewer,
};

registry.category("fields").add("x2_many_media_viewer", x2ManyMediaViewer);
