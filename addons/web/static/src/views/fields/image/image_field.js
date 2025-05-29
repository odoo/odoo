import { isMobileOS } from "@web/core/browser/feature_detection";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { imageUrl } from "@web/core/utils/urls";
import { isBinarySize } from "@web/core/utils/binary";
import { FileUploader } from "../file_handler";
import { standardFieldProps } from "../standard_field_props";

import { Component, useState, onWillRender } from "@odoo/owl";
const { DateTime } = luxon;

export const fileTypeMagicWordMap = {
    "/": "jpg",
    R: "gif",
    i: "png",
    P: "svg+xml",
    U: "webp",
};
const placeholder = "/web/static/img/placeholder.png";

export class ImageField extends Component {
    static template = "web.ImageField";
    static components = {
        FileUploader,
    };
    static props = {
        ...standardFieldProps,
        alt: { type: String, optional: true },
        enableZoom: { type: Boolean, optional: true },
        imgClass: { type: String, optional: true },
        zoomDelay: { type: Number, optional: true },
        previewImage: { type: String, optional: true },
        acceptedFileExtensions: { type: String, optional: true },
        width: { type: Number, optional: true },
        height: { type: Number, optional: true },
        reload: { type: Boolean, optional: true },
        convertToWebp: { type: Boolean, optional: true },
    };
    static defaultProps = {
        acceptedFileExtensions: "image/*",
        alt: _t("Binary file"),
        imgClass: "",
        reload: true,
    };

    setup() {
        this.notification = useService("notification");
        this.orm = useService("orm");
        this.isMobile = isMobileOS();
        this.state = useState({
            isValid: true,
        });
        this.lastURL = undefined;

        if (this.fieldType === "many2one" && !this.props.previewImage) {
            throw new Error(
                "ImageField: previewImage must be provided when set on a many2one field"
            );
        }
        const field = this.props.record.fields[this.props.name];
        if (field.related?.includes(".")) {
            this.lastUpdate = DateTime.now();
            let key = this.props.value;
            onWillRender(() => {
                const nextKey = this.props.value;

                if (key !== nextKey) {
                    this.lastUpdate = DateTime.now();
                }

                key = nextKey;
            });
        }
    }

    get imgAlt() {
        if (this.fieldType === "many2one" && this.props.record.data[this.props.name]) {
            return this.props.record.data[this.props.name][1];
        }
        return this.props.alt;
    }

    get imgClass() {
        return ["img", "img-fluid"].concat(this.props.imgClass.split(" ")).join(" ");
    }

    get fieldType() {
        return this.props.record.fields[this.props.name].type;
    }

    get rawCacheKey() {
        return this.lastUpdate || this.props.record.data.write_date;
    }

    get sizeStyle() {
        let style = "";
        if (this.props.width) {
            style += `max-width: ${this.props.width}px;`;
            if (!this.props.height) {
                style += `height: auto; max-height: 100%;`;
            }
        }
        if (this.props.height) {
            style += `max-height: ${this.props.height}px;`;
            if (!this.props.width) {
                style += `width: auto; max-width: 100%;`;
            }
        }
        return style;
    }
    get hasTooltip() {
        return this.props.enableZoom && this.props.record.data[this.props.name];
    }
    get tooltipAttributes() {
        const fieldName = this.fieldType === "many2one" ? this.props.previewImage : this.props.name;
        return {
            template: "web.ImageZoomTooltip",
            info: JSON.stringify({ url: this.getUrl(fieldName) }),
        };
    }

    getUrl(imageFieldName) {
        if (!this.props.reload && this.lastURL) {
            return this.lastURL;
        }
        if (!this.props.record.data[this.props.name] || !this.state.isValid) {
            return placeholder;
        }
        if (this.fieldType === "many2one") {
            this.lastURL = imageUrl(
                this.props.record.fields[this.props.name].relation,
                this.props.record.data[this.props.name][0],
                imageFieldName,
                { unique: this.rawCacheKey }
            );
        } else if (isBinarySize(this.props.record.data[this.props.name])) {
            this.lastURL = imageUrl(
                this.props.record.resModel,
                this.props.record.resId,
                imageFieldName,
                { unique: this.rawCacheKey }
            );
        } else {
            // Use magic-word technique for detecting image type
            const magic = fileTypeMagicWordMap[this.props.record.data[this.props.name][0]] || "png";
            this.lastURL = `data:image/${magic};base64,${this.props.record.data[this.props.name]}`;
        }
        return this.lastURL;
    }
    onFileRemove() {
        this.state.isValid = true;
        this.props.record.update({ [this.props.name]: false });
    }
    async onFileUploaded(info) {
        this.state.isValid = true;
        if (
            this.props.convertToWebp &&
            !["image/gif", "image/svg+xml", "image/webp"].includes(info.type)
        ) {
            const image = document.createElement("img");
            image.src = `data:${info.type};base64,${info.data}`;
            await new Promise((resolve) => image.addEventListener("load", resolve));

            const canvas = document.createElement("canvas");
            canvas.width = image.width;
            canvas.height = image.height;
            const ctx = canvas.getContext("2d");
            ctx.drawImage(image, 0, 0);

            info.data = canvas.toDataURL("image/webp", 0.75).split(",")[1];
            info.type = "image/webp";
            info.name = info.name.replace(/\.[^/.]+$/, ".webp");
        }
        if (info.type === "image/webp") {
            // Generate alternate sizes and format for reports.
            const image = document.createElement("img");
            image.src = `data:image/webp;base64,${info.data}`;
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
                ctx.fillStyle = "transparent";
                ctx.fillRect(0, 0, canvas.width, canvas.height);
                ctx.imageSmoothingEnabled = true;
                ctx.imageSmoothingQuality = "high";
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
                const [resizedId] = await this.orm.call("ir.attachment", "create_unique", [
                    [
                        {
                            name: info.name,
                            description: size === originalSize ? "" : `resize: ${size}`,
                            datas:
                                size === originalSize
                                    ? info.data
                                    : canvas.toDataURL("image/webp", 0.75).split(",")[1],
                            res_id: referenceId,
                            res_model: "ir.attachment",
                            mimetype: "image/webp",
                        },
                    ],
                ]);
                referenceId = referenceId || resizedId; // Keep track of original.
                // Converted to JPEG for use in PDF files, alpha values will default to white
                await this.orm.call("ir.attachment", "create_unique", [
                    [
                        {
                            name: info.name.replace(/\.webp$/, ".jpg"),
                            description: "format: jpeg",
                            datas: canvas.toDataURL("image/jpeg", 0.75).split(",")[1],
                            res_id: resizedId,
                            res_model: "ir.attachment",
                            mimetype: "image/jpeg",
                        },
                    ],
                ]);
            }
        }
        this.props.record.update({ [this.props.name]: info.data });
    }
    onLoadFailed() {
        this.state.isValid = false;
    }
}

export const imageField = {
    component: ImageField,
    displayName: _t("Image"),
    supportedAttributes: [
        {
            label: _t("Alternative text"),
            name: "alt",
            type: "string",
        },
    ],
    supportedOptions: [
        {
            label: _t("Reload"),
            name: "reload",
            type: "boolean",
            default: true,
        },
        {
            label: _t("Enable zoom"),
            name: "zoom",
            type: "boolean",
        },
        {
            label: _t("Convert to webp"),
            name: "convert_to_webp",
            type: "boolean",
        },
        {
            label: _t("Zoom delay"),
            name: "zoom_delay",
            type: "number",
            help: _t("Delay the apparition of the zoomed image with a value in milliseconds"),
        },
        {
            label: _t("Accepted file extensions"),
            name: "accepted_file_extensions",
            type: "string",
        },
        {
            label: _t("Size"),
            name: "size",
            type: "selection",
            choices: [
                { label: _t("Small"), value: "[0,90]" },
                { label: _t("Medium"), value: "[0,180]" },
                { label: _t("Large"), value: "[0,270]" },
            ],
        },
        {
            label: _t("Preview image"),
            name: "preview_image",
            type: "field",
            availableTypes: ["binary"],
        },
    ],
    supportedTypes: ["binary", "many2one"],
    fieldDependencies: [{ name: "write_date", type: "datetime" }],
    isEmpty: () => false,
    extractProps: ({ attrs, options }) => ({
        alt: attrs.alt,
        enableZoom: options.zoom,
        convertToWebp: options.convert_to_webp,
        imgClass: options.img_class,
        zoomDelay: options.zoom_delay,
        previewImage: options.preview_image,
        acceptedFileExtensions: options.accepted_file_extensions,
        width: options.size && Boolean(options.size[0]) ? options.size[0] : attrs.width,
        height: options.size && Boolean(options.size[1]) ? options.size[1] : attrs.height,
        reload: "reload" in options ? Boolean(options.reload) : true,
    }),
};

registry.category("fields").add("image", imageField);
