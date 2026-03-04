import { useChildSubEnv } from "@web/owl2/utils";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { X2ManyField, x2ManyField } from "@web/views/fields/x2many/x2many_field";
import { CustomMediaDialog } from "./custom_media_dialog";
import { getDataURLFromFile } from "@web/core/utils/urls";
import { saveMultipleAttachments } from "@web/core/utils/image_library";

export class X2ManyMediaViewer extends X2ManyField {
    static template = "html_editor.X2ManyMediaViewer";
    static props = {
        ...X2ManyField.props,
        convertToWebp: { type: Boolean, optional: true },
    };

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
        this.dialogs.add(CustomMediaDialog, this.mediaDialogProps);
    }

    get mediaDialogProps() {
        return {
            save: (el) => {}, // Simple rebound to fake its execution
            multiImages: true,
            visibleTabs: ["IMAGES", "VIDEOS"],
            imageSave: this.onImageSave.bind(this),
            videoSave: this.onVideoSave.bind(this),
        };
    }

    async onVideoSave(videosInfo) {
        const videoInfo = videosInfo[0];
        let thumbnailData = null;
        if (videoInfo?.thumbnailUrl) {
            const fetchResult = await fetch(videoInfo.thumbnailUrl);
            const blob = await fetchResult.blob();
            thumbnailData = await getDataURLFromFile(blob);
        }

        const productImageRecords = this.props.record.data[this.props.name];
        productImageRecords.addNewRecord({ position: "bottom" }).then(async (record) => {
            record.update({
                name: videoInfo.platform + " - [Video]",
                video_url: videoInfo.embedUrl,
                image_1920: thumbnailData ? thumbnailData.split(",")[1] : null,
            });
        });
    }

    async onImageSave(attachments) {
        await saveMultipleAttachments(this.env, {
            attachments,
            targetRecord: this.props.record,
            targetFieldName: this.props.name,
            convertToWebp: this.props.convertToWebp,
        });
    }

    async onAdd({ context, editable } = {}) {
        this.addMedia();
    }
}

export const x2ManyMediaViewer = {
    ...x2ManyField,
    component: X2ManyMediaViewer,
    relatedFields: () => [{ name: "name" }, { name: "image_1920" }, { name: "video_url" }],
    extractProps: (
        { attrs, relatedFields, viewMode, views, widget, options, string },
        dynamicInfo
    ) => {
        const x2ManyFieldProps = x2ManyField.extractProps(
            { attrs, relatedFields, viewMode, views, widget, options, string },
            dynamicInfo
        );
        return {
            ...x2ManyFieldProps,
            convertToWebp: options.convert_to_webp,
        };
    },
};

registry.category("fields").add("x2_many_media_viewer", x2ManyMediaViewer);
