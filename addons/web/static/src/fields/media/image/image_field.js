// @ts-check
/** @odoo-module native */

import { status, useState } from "@odoo/owl";
import { isMobileOS } from "@web/core/browser/feature_detection";
import { FileUploader } from "@web/core/file_upload/file_handler";
import { DateTime } from "@web/core/l10n/luxon";
import { _t } from "@web/core/translation";
import { isBinarySize } from "@web/core/utils/format/binary";
import { useService } from "@web/core/utils/hooks";
import { imageUrl } from "@web/core/utils/urls";
import { registerField } from "@web/fields/_registry";
import { FieldComponent } from "@web/fields/field_component";
import { fieldHandleFor } from "@web/fields/field_handle";
import {
    acceptedFileExtensionsOption,
    imageSizeOption,
} from "@web/fields/field_options";
import {
    convertUploadToWebp,
    createWebpVariantAttachments,
    ImageDecodeError,
} from "@web/fields/media/image/image_variants";
import { standardFieldProps } from "@web/fields/standard_field_props";

/** @type {Record<string, string>} */
export const fileTypeMagicWordMap = {
    "/": "jpg",
    R: "gif",
    i: "png",
    P: "svg+xml",
    U: "webp",
};
export const IMAGE_PLACEHOLDER = "/web/static/img/placeholder.png";

/**
 * @param {string} value
 * @param {{ model: string, resId: number | false, field: string, unique?: any }} location
 * @returns {string}
 */
export function binaryImageSrc(value, { model, resId, field, unique }) {
    if (isBinarySize(value)) {
        return imageUrl(model, /** @type {number} */ (resId), field, { unique });
    }
    const magic = fileTypeMagicWordMap[value[0]] || "png";
    return `data:image/${magic};base64,${value}`;
}

export class ImageField extends FieldComponent {
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

    /** @type {import("services").ServiceFactories["notification"]} */
    notification;
    /** @type {import("services").ServiceFactories["orm"]} */
    orm;
    /** @type {{ failedVersionId: number | null }} */
    state;

    setup() {
        this.notification = useService("notification");
        this.orm = useService("orm");
        this.isMobile = isMobileOS();
        this.state = useState({
            failedVersionId: null,
        });

        if (this.fieldType === "many2one" && !this.props.previewImage) {
            throw new Error(
                "ImageField: previewImage must be provided when set on a many2one field",
            );
        }
        const field = this.field.definition;
        const isDottedRelated = field.related?.includes(".");
        this.bustsCacheOnValueChange = isDottedRelated || this.fieldType === "many2one";
    }

    /**
     * The image the field currently shows: its cache-busting key, its urls,
     * and whether it failed to load are all tied to one record and value.
     *
     * @returns {{ id: number, resId: any, value: any, uniqueId: any, urls: Map<string, string> }}
     */
    get imageVersion() {
        const { record } = this.props;
        const value = fieldHandleFor(record, this.props.name).value;
        const current = this._imageVersion;
        if (
            current &&
            current.resId === record.resId &&
            !this.valueChanged(current.value, value)
        ) {
            return current;
        }
        this._imageVersion = {
            id: (current?.id ?? 0) + 1,
            resId: record.resId,
            value,
            uniqueId:
                current &&
                current.resId === record.resId &&
                this.bustsCacheOnValueChange
                    ? DateTime.now()
                    : record.data.write_date,
            urls: new Map(),
        };
        return this._imageVersion;
    }

    /**
     * @param {any} value
     * @param {any} nextValue
     */
    valueChanged(value, nextValue) {
        return this.fieldType === "many2one"
            ? value?.id !== nextValue?.id ||
                  value?.display_name !== nextValue?.display_name
            : value !== nextValue;
    }

    /** @returns {boolean} */
    get isValid() {
        return this.state.failedVersionId !== this.imageVersion.id;
    }

    get imgAlt() {
        if (this.fieldType === "many2one" && this.field.value) {
            return this.field.value.display_name;
        }
        return this.props.alt;
    }

    get imgClass() {
        return ["img", "img-fluid", ...this.props.imgClass.split(" ")]
            .filter(Boolean)
            .join(" ");
    }

    get fieldType() {
        return this.field.type;
    }

    get rawCacheKey() {
        return this.imageVersion.uniqueId;
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
        return this.props.enableZoom && this.field.value;
    }
    /** @returns {Record<string, string>} */
    get tooltipAttributes() {
        if (!this.hasTooltip) {
            return {};
        }
        const fieldName =
            this.fieldType === "many2one" ? this.props.previewImage : this.props.name;
        return {
            "data-tooltip-template": "web.ImageZoomTooltip",
            "data-tooltip-info": JSON.stringify({ url: this.getUrl(fieldName) }),
            ...(this.props.zoomDelay
                ? { "data-tooltip-delay": String(this.props.zoomDelay) }
                : {}),
        };
    }

    getUrl(imageFieldName) {
        if (!this.field.value || !this.isValid) {
            return IMAGE_PLACEHOLDER;
        }
        const { urls } = this.imageVersion;
        if (!this.props.reload && urls.has(imageFieldName)) {
            return /** @type {string} */ (urls.get(imageFieldName));
        }
        const url =
            this.fieldType === "many2one"
                ? imageUrl(
                      this.field.definition.relation,
                      this.field.value.id,
                      imageFieldName,
                      { unique: this.rawCacheKey },
                  )
                : binaryImageSrc(this.field.value, {
                      model: this.props.record.resModel,
                      resId: this.props.record.resId,
                      field: imageFieldName,
                      unique: this.rawCacheKey,
                  });
        urls.set(imageFieldName, url);
        return url;
    }
    onFileRemove() {
        this.state.failedVersionId = null;
        this.field.update(false);
    }
    async onFileUploaded(info) {
        const record = this.props.record;
        this.state.failedVersionId = null;
        try {
            if (this.props.convertToWebp) {
                info = await convertUploadToWebp(info);
            }
            if (info.type === "image/webp") {
                await createWebpVariantAttachments(this.orm, info);
            }
        } catch (error) {
            if (!(error instanceof ImageDecodeError)) {
                throw error;
            }
            this.notification.add(_t("Could not display the selected image"), {
                type: "danger",
            });
            return;
        }
        if (record !== this.props.record || status(this) === "destroyed") {
            return;
        }
        this.field.update(info.data);
    }
    onLoadFailed() {
        this.state.failedVersionId = this.imageVersion.id;
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
            help: _t(
                "Delay the apparition of the zoomed image with a value in milliseconds",
            ),
        },
        acceptedFileExtensionsOption(),
        imageSizeOption(),
        {
            label: _t("Preview image"),
            name: "preview_image",
            type: "field",
            availableTypes: ["binary"],
        },
        {
            label: _t("Image class"),
            name: "img_class",
            type: "string",
            help: _t("Extra CSS classes set on the <img> element."),
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
    }),
};

registerField("image", /** @type {any} */ (imageField));
