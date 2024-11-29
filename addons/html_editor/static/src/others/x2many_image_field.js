import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { ImageField, imageField } from "@web/views/fields/image/image_field";
import { CustomMediaDialog } from "./custom_media_dialog";
import { getVideoUrl } from "@html_editor/utils/url";

export class X2ManyImageField extends ImageField {
    static template = "html_editor.ImageField";
    setup() {
        super.setup();
        this.orm = useService("orm");
        this.dialog = useService("dialog");
    }

    /**
     * New method and a new edit button is introduced here to overwrite,
     * standard behavior of opening file input box in order to update a record.
     */
    onFileEdit(ev) {
        const isVideo = this.props.record.data.video_url;
        let mediaEl;
        if (isVideo) {
            mediaEl = document.createElement("img");
            mediaEl.dataset.src = this.props.record.data.video_url;
        }
        this.dialog.add(CustomMediaDialog, {
            noDocuments: true,
            noIcons: true,
            media: mediaEl,
            activeTab: isVideo ? "VIDEOS" : "IMAGES",
            save: (el) => {}, // Simple rebound to fake its execution
            imageSave: this.onImageSave.bind(this),
            videoSave: this.onVideoSave.bind(this),
        });
    }

    async onImageSave(attachment) {
        const attachmentRecord = await this.orm.searchRead(
            "ir.attachment",
            [["id", "=", attachment[0].id]],
            ["id", "datas", "name"],
            {}
        );
        if (!attachmentRecord[0].datas) {
            // URL type attachments are mostly demo records which don't have any ir.attachment datas
            // TODO: make it work with URL type attachments
            return this.notification.add(`Cannot add URL type attachment "${attachmentRecord[0].name}". Please try to reupload this image.`, {
                type: "warning",
            });
        }
        await this.props.record.update({
            [this.props.name]: attachmentRecord[0].datas,
            name: attachmentRecord[0].name,
        });
    }

    async onVideoSave(videoInfo) {
        const url = getVideoUrl(videoInfo[0].platform, videoInfo[0].videoId, videoInfo[0].params);
        await this.props.record.update({
            video_url: url.href,
            name: videoInfo[0].platform + " - [Video]",
        });
    }

    onFileRemove() {
        const parentRecord = this.props.record._parentRecord.data;
        parentRecord[this.env.parentField].delete(this.props.record);
    }
}

export const x2ManyImageField = {
    ...imageField,
    component: X2ManyImageField,
};

registry.category("fields").add("x2_many_image", x2ManyImageField);
