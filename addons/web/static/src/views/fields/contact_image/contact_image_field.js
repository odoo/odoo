import { isBinarySize } from "@web/core/utils/binary";
import { registry } from "@web/core/registry";
import { imageUrl } from "@web/core/utils/urls";
import { ImageField, imageField, fileTypeMagicWordMap } from "@web/views/fields/image/image_field";

export class ContactImageField extends ImageField {
    static template = "web.ContactImageField";

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
                    { unique: this.rawCacheKey }
                );
            } else {
                const magic =
                    fileTypeMagicWordMap[this.props.record.data[imageFieldName][0]] || "png";
                this.lastURL = `data:image/${magic};base64,${this.props.record.data[imageFieldName]}`;
            }
            return this.lastURL;
        }
        return super.getUrl(imageFieldName);
    }

    get imgClass() {
        let classes = super.imgClass;
        if (!this.props.record.data[this.props.name] || !this.state.isValid) {
            classes += " opacity-100 opacity-25-hover";
        }
        return classes;
    }

    get containsValidImage() {
        return this.props.record.data[this.props.name] && this.state.isValid;
    }
}

export const contactImageField = {
    ...imageField,
    component: ContactImageField,
};

registry.category("fields").add("contact_image", contactImageField);
