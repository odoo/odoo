import { isMobileOS } from "@web/core/browser/feature_detection";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { imageUrl } from "@web/core/utils/urls";
import { isBinarySize } from "@web/core/utils/binary";
import { generateImageVariants } from "@web/core/utils/image_library";
import { FileUploader } from "../file_handler";
import { standardFieldProps } from "../standard_field_props";

import { Component, props, proxy, t } from "@odoo/owl";

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
    props = props({
        ...standardFieldProps,
        alt: t.string().optional(_t("Binary file")),
        enableZoom: t.boolean().optional(),
        imgClass: t.string().optional(""),
        zoomDelay: t.number().optional(),
        previewImage: t.string().optional(),
        acceptedFileExtensions: t.string().optional("image/*"),
        width: t.number().optional(),
        height: t.number().optional(),
        reload: t.boolean().optional(true),
        convertToWebp: t.boolean().optional(),
        fileNameField: t.string().optional(),
    });

    setup() {
        this.notification = useService("notification");
        this.orm = useService("orm");
        this.isMobile = isMobileOS();
        this.state = proxy({
            isValid: true,
        });
        this.lastURL = undefined;

        if (this.fieldType === "many2one" && !this.props.previewImage) {
            throw new Error(
                "ImageField: previewImage must be provided when set on a many2one field"
            );
        }
        const field = this.props.record.fields[this.props.name];
        this.isImageOnAnotherRecord = field.related?.includes(".") || this.fieldType === "many2one";
    }

    get imgAlt() {
        if (this.fieldType === "many2one" && this.props.record.data[this.props.name]) {
            return this.props.record.data[this.props.name].display_name;
        }
        return this.props.alt;
    }

    get imgClass() {
        return ["img", "img-fluid"].concat(this.props.imgClass.split(" ")).join(" ");
    }

    get containerClass() {
        let containerClass =
            "position-absolute d-flex justify-content-between w-100 bottom-0 opacity-0 opacity-100-hover";
        if (this.isMobile) {
            containerClass += " o_mobile_controls";
        }
        return containerClass;
    }

    get fieldType() {
        return this.props.record.fields[this.props.name].type;
    }

    get rawCacheKey() {
        if (this.isImageOnAnotherRecord) {
            return null;
        }
        return this.props.record.data.write_date;
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
                this.props.record.data[this.props.name].id,
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

        const { fileNameField, record } = this.props;
        const changes = { [this.props.name]: false };
        if (fileNameField in record.fields) {
            changes[fileNameField] = false;
        }
        record.update(changes);
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

            info.data = canvas.toDataURL("image/webp").split(",")[1];
            info.type = "image/webp";
            info.name = info.name.replace(/\.[^/.]+$/, ".webp");
        }
        if (info.type === "image/webp") {
            // Generate alternate sizes and format for reports.
            const variants = await generateImageVariants({
                source: { data: info.data, mimetype: "image/webp" },
                name: info.name,
                smoothing: "high",
            });
            await this.orm.call("ir.attachment", "web_create_image_variants", [variants]);
        }
        const { fileNameField, record } = this.props;
        const changes = { [this.props.name]: info.data || false };
        if (
            this.fieldType !== "many2one" &&
            fileNameField in record.fields &&
            record.data[fileNameField] !== info.name
        ) {
            changes[fileNameField] = info.name || "";
        }
        record.update(changes);
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
        width: options.size && Boolean(options.size[0]) ? options.size[0] : undefined,
        height: options.size && Boolean(options.size[1]) ? options.size[1] : undefined,
        reload: "reload" in options ? Boolean(options.reload) : true,
        fileNameField: attrs.filename,
    }),
};

registry.category("fields").add("image", imageField);
