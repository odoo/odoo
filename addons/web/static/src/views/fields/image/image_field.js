/** @odoo-module **/

import { isMobileOS } from "@web/core/browser/feature_detection";
import { _lt } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { url } from "@web/core/utils/urls";
import { isBinarySize } from "@web/core/utils/binary";
import { FileUploader } from "../file_handler";
import { standardFieldProps } from "../standard_field_props";

import { Component, useState, onWillUpdateProps } from "@odoo/owl";
const { DateTime } = luxon;

export const fileTypeMagicWordMap = {
    "/": "jpg",
    R: "gif",
    i: "png",
    P: "svg+xml",
};
const placeholder = "/web/static/img/placeholder.png";

/**
 * Formats a value to be injected in the image's url in order for that url
 * to be correctly cached and discarded by the browser (the browser caches
 * fetch requests with the url as key).
 *
 * For records, a not-so-bad approximation is to compute that key on the basis
 * of the record's write_date field.
 */
export function imageCacheKey(value) {
    if (value instanceof DateTime) {
        return value.ts;
    }
    return "";
}

export class ImageField extends Component {
    static template = "web.ImageField";
    static components = {
        FileUploader,
    };
    static props = {
        ...standardFieldProps,
        enableZoom: { type: Boolean, optional: true },
        zoomDelay: { type: Number, optional: true },
        previewImage: { type: String, optional: true },
        acceptedFileExtensions: { type: String, optional: true },
        width: { type: Number, optional: true },
        height: { type: Number, optional: true },
    };
    static defaultProps = {
        acceptedFileExtensions: "image/*",
    };

    setup() {
        this.notification = useService("notification");
        this.isMobile = isMobileOS();
        this.state = useState({
            isValid: true,
        });

        this.rawCacheKey = this.props.record.data.write_date;
        onWillUpdateProps((nextProps) => {
            const { record } = this.props;
            const { record: nextRecord } = nextProps;
            if (record.resId !== nextRecord.resId || nextRecord.mode === "readonly") {
                this.rawCacheKey = nextRecord.data.write_date;
            }
        });
    }

    get sizeStyle() {
        let style = "";
        if (this.props.width) {
            style += `max-width: ${this.props.width}px;`;
        }
        if (this.props.height) {
            style += `max-height: ${this.props.height}px;`;
        }
        return style;
    }
    get hasTooltip() {
        return this.props.enableZoom && this.props.readonly && this.props.value;
    }
    get tooltipAttributes() {
        return {
            template: "web.ImageZoomTooltip",
            info: JSON.stringify({ url: this.getUrl(this.props.name) }),
        };
    }

    getUrl(previewFieldName) {
        if (this.state.isValid && this.props.value) {
            if (isBinarySize(this.props.value)) {
                if (!this.rawCacheKey) {
                    this.rawCacheKey = this.props.record.data.write_date;
                }
                return url("/web/image", {
                    model: this.props.record.resModel,
                    id: this.props.record.resId,
                    field: previewFieldName,
                    unique: imageCacheKey(this.rawCacheKey),
                });
            } else {
                // Use magic-word technique for detecting image type
                const magic = fileTypeMagicWordMap[this.props.value[0]] || "png";
                return `data:image/${magic};base64,${this.props.value}`;
            }
        }
        return placeholder;
    }
    onFileRemove() {
        this.state.isValid = true;
        this.props.record.update({ [this.props.name]: false });
    }
    onFileUploaded(info) {
        this.state.isValid = true;
        // Invalidate the `rawCacheKey`.
        this.rawCacheKey = null;
        this.props.record.update({ [this.props.name]: info.data });
    }
    onLoadFailed() {
        this.state.isValid = false;
        this.notification.add(this.env._t("Could not display the selected image"), {
            type: "danger",
        });
    }
}

export const imageField = {
    component: ImageField,
    displayName: _lt("Image"),
    supportedTypes: ["binary"],
    fieldDependencies: [{ name: "write_date", type: "datetime" }],
    extractProps: ({ attrs }) => ({
        enableZoom: attrs.options.zoom,
        zoomDelay: attrs.options.zoom_delay,
        previewImage: attrs.options.preview_image,
        acceptedFileExtensions: attrs.options.accepted_file_extensions,
        width:
            attrs.options.size && Boolean(attrs.options.size[0])
                ? attrs.options.size[0]
                : attrs.width,
        height:
            attrs.options.size && Boolean(attrs.options.size[1])
                ? attrs.options.size[1]
                : attrs.height,
    }),
};

registry.category("fields").add("image", imageField);
registry.category("fields").add("kanban.image", imageField); // FIXME WOWL: s.t. we don't use the legacy one
