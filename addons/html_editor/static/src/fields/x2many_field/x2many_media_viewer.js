import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { X2ManyField, x2ManyField } from "@web/views/fields/x2many/x2many_field";
import { getVideoUrl } from "@html_editor/utils/url";
import { useChildSubEnv } from "@odoo/owl";
import { CustomMediaDialog } from "./custom_media_dialog";

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
        const attachmentIds = attachments.map((attachment) => attachment.id);
        const attachmentRecords = await this.orm.searchRead(
            "ir.attachment",
            [["id", "in", attachmentIds]],
            ["id", "datas", "name", "mimetype"],
            {}
        );
        for (const attachment of attachmentRecords) {
            const imageList = this.props.record.data[this.props.name];
            if (!attachment.datas) {
                // URL type attachments are mostly demo records which don't have any ir.attachment datas
                // TODO: make it work with URL type attachments
                return this.notification.add(
                    `Cannot add URL type attachment "${attachment.name}". Please try to reupload this image.`,
                    {
                        type: "warning",
                    }
                );
            }
            if (
                this.props.convertToWebp &&
                !["image/gif", "image/svg+xml"].includes(attachment.mimetype)
            ) {
                // This method is widely adapted from onFileUploaded in ImageField.
                // Upon change, make sure to verify whether the same change needs
                // to be applied on both sides.
                // Generate alternate sizes and format for reports.
                const image = document.createElement("img");
                image.src = `data:${attachment.mimetype};base64,${attachment.datas}`;
                await new Promise((resolve) => image.addEventListener("load", resolve));

                const originalSize = Math.max(image.width, image.height);
                const smallerSizes = [1024, 512, 256, 128].filter((size) => size < originalSize);
                let referenceId = undefined;

                for (const size of [originalSize, ...smallerSizes]) {
                    const ratio = size / originalSize;
                    const canvas = document.createElement("canvas");
                    canvas.width = image.width * ratio;
                    canvas.height = image.height * ratio;
                    const ctx = canvas.getContext("2d");
                    ctx.drawImage(
                        image,
                        0,
                        0,
                        image.width,
                        image.height,
                        0,
                        0,
                        canvas.width,
                        canvas.height
                    );

                    // WebP format
                    const webpData = canvas.toDataURL("image/webp", 0.75).split(",")[1];
                    const [resizedId] = await this.orm.call("ir.attachment", "create_unique", [
                        [
                            {
                                name: attachment.name.replace(/\.[^/.]+$/, ".webp"),
                                description: size === originalSize ? "" : `resize: ${size}`,
                                datas: webpData,
                                res_id: referenceId,
                                res_model: "ir.attachment",
                                mimetype: "image/webp",
                            },
                        ],
                    ]);

                    referenceId = referenceId || resizedId;

                    // JPEG format for compatibility
                    const jpegData = canvas.toDataURL("image/jpeg", 0.75).split(",")[1];
                    await this.orm.call("ir.attachment", "create_unique", [
                        [
                            {
                                name: attachment.name.replace(/\.[^/.]+$/, ".jpg"),
                                description: `resize: ${size} - format: jpeg`,
                                datas: jpegData,
                                res_id: resizedId,
                                res_model: "ir.attachment",
                                mimetype: "image/jpeg",
                            },
                        ],
                    ]);
                }
                const canvas = document.createElement("canvas");
                canvas.width = image.width;
                canvas.height = image.height;
                const ctx = canvas.getContext("2d");
                ctx.drawImage(image, 0, 0, image.width, image.height);

                const webpData = canvas.toDataURL("image/webp", 0.75).split(",")[1];
                attachment.datas = webpData;
                attachment.mimetype = "image/webp";
                attachment.name = attachment.name.replace(/\.[^/.]+$/, ".webp");
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
        }
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
