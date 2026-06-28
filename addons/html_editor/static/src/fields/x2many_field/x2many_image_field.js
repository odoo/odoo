import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { ImageField, imageField } from "@web/views/fields/image/image_field";
import { CustomMediaDialog } from "./custom_media_dialog";
import { getDataURLFromFile } from "@web/core/utils/urls";
import { saveSingleAttachment } from "@web/core/utils/image_library";

export class X2ManyImageField extends ImageField {
    static template = "html_editor.ImageField";
    static props = {
        ...ImageField.props,
        setAttachmentId: { type: Boolean, optional: true },
        onlyImage: { type: Boolean, optional: true },
    };

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
        this.dialog.add(CustomMediaDialog, this.mediaDialogProps);
    }

    get mediaDialogProps() {
        const isVideo = this.props.record.data.video_url;
        let mediaEl;
        if (isVideo) {
            mediaEl = document.createElement("img");
            mediaEl.dataset.src = this.props.record.data.video_url;
        }
        return {
            visibleTabs: this.props.onlyImage ? ["IMAGES"] : ["IMAGES", "VIDEOS"],
            media: mediaEl,
            activeTab: isVideo ? "VIDEOS" : "IMAGES",
            save: (el) => {}, // Simple rebound to fake its execution
            imageSave: this.onImageSave.bind(this),
            videoSave: this.onVideoSave.bind(this),
            document: window.document,
        };
    }

    async onImageSave(attachments) {
        await saveSingleAttachment(this.env, {
            attachment: attachments[0],
            targetRecord: this.props.record,
            targetFieldName: this.props.name,
            setAttachmentId: this.props.setAttachmentId,
            changeRecordName: true,
        });
    }

    async onVideoSave(videosInfo) {
        const videoInfo = videosInfo[0];
        let thumbnailData = null;
        if (videoInfo?.thumbnailUrl) {
            const fetchResult = await fetch(videoInfo.thumbnailUrl);
            const blob = await fetchResult.blob();
            thumbnailData = await getDataURLFromFile(blob);
        }

        await this.props.record.update({
            name: videoInfo.platform + " - [Video]",
            video_url: videoInfo.embedUrl,
            image_1920: thumbnailData ? thumbnailData.split(",")[1] : null,
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
    extractProps: (
        { attrs, relatedFields, viewMode, views, widget, options, string },
        dynamicInfo
    ) => {
        const x2ManyFieldProps = imageField.extractProps(
            { attrs, relatedFields, viewMode, views, widget, options, string },
            dynamicInfo
        );
        return {
            ...x2ManyFieldProps,
            setAttachmentId: options.set_attachment_id,
            onlyImage: options.only_image,
        };
    },
};

registry.category("fields").add("x2_many_image", x2ManyImageField);
