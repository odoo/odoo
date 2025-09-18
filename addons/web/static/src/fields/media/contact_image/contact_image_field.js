// @ts-check

/** @module @web/fields/media/contact_image/contact_image_field - Image field variant with fallback to a preview image when empty */

import { registry } from "@web/core/registry";
import { isBinarySize } from "@web/core/utils/format/binary";
import { imageUrl } from "@web/core/utils/urls";
import { ImageField, imageField } from "@web/fields/media/image/image_field";

export class ContactImageField extends ImageField {
    static template = "web.ContactImageField";

    /**
     * @param {string} imageFieldName Field name to fetch the image from
     * @returns {string} Image URL, falling back to preview image when primary is empty
     */
    getUrl(imageFieldName) {
        if (
            this.props.previewImage &&
            (!this.props.record.data[this.props.name] || !this.state.isValid)
        ) {
            if (isBinarySize(this.props.record.data[imageFieldName])) {
                this.lastURL = imageUrl(
                    this.props.record.resModel,
                    this.props.record.resId,
                    imageFieldName,
                    { unique: this.rawCacheKey },
                );
            } else {
                this.lastURL = `data:image/png;base64,${this.props.record.data[imageFieldName]}`;
            }
            return this.lastURL;
        }
        return super.getUrl(imageFieldName);
    }

    /** @returns {string} CSS classes with reduced opacity when image is missing */
    get imgClass() {
        let classes = super.imgClass;
        if (!this.props.record.data[this.props.name] || !this.state.isValid) {
            classes += " opacity-100 opacity-25-hover";
        }
        return classes;
    }

    /** @returns {boolean} Whether the field contains valid image data */
    get containsValidImage() {
        return this.props.record.data[this.props.name] && this.state.isValid;
    }
}

export const contactImageField = {
    ...imageField,
    component: ContactImageField,
};

registry.category("fields").add("contact_image", contactImageField);
