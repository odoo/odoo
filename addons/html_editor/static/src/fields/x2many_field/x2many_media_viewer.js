import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { X2ManyField, x2ManyField } from "@web/views/fields/x2many/x2many_field";
import { getVideoUrl } from "@html_editor/utils/url";
import { useChildSubEnv } from "@odoo/owl";
import { CustomMediaDialog } from "./custom_media_dialog";
import { save } from "@web/core/utils/image_library"

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
        this.dialogs.add(CustomMediaDialog, {
            save: (el) => {}, // Simple rebound to fake its execution
            multiImages: true,
            visibleTabs: ["IMAGES", "VIDEOS"],
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
        await save(this.env, {
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
