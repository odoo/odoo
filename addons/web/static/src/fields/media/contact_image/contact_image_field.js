// @ts-check
/** @odoo-module native */

import { registerField } from "@web/fields/_registry";
import {
    binaryImageSrc,
    ImageField,
    imageField,
} from "@web/fields/media/image/image_field";

export class ContactImageField extends ImageField {
    static template = "web.ContactImageField";

    /**
     * @param {string} imageFieldName
     * @returns {string}
     */
    getUrl(imageFieldName) {
        if (this.props.previewImage && (!this.field.value || !this.isValid)) {
            const previewData = this.props.record.data[imageFieldName];
            if (previewData) {
                const url = binaryImageSrc(previewData, {
                    model: this.props.record.resModel,
                    resId: this.props.record.resId,
                    field: imageFieldName,
                    unique: this.rawCacheKey,
                });
                return url;
            }
        }
        return super.getUrl(imageFieldName);
    }

    /** @returns {string} */
    get imgClass() {
        let classes = super.imgClass;
        if (!this.field.value || !this.isValid) {
            classes += " opacity-100 opacity-25-hover";
        }
        return classes;
    }

    /** @returns {boolean} */
    get containsValidImage() {
        return this.field.value && this.isValid;
    }
}

/** @type {import("registries").FieldsRegistryItemShape} */
const contactImageField = {
    ...imageField,
    component: ContactImageField,
    fieldDependencies: ({ options }) => [
        { name: "write_date", type: "datetime" },
        ...(options.preview_image
            ? [{ name: options.preview_image, optional: true, readonly: true }]
            : []),
    ],
};

registerField("contact_image", contactImageField);
