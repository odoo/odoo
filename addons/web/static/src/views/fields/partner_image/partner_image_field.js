import { registry } from "@web/core/registry";
import { ImageField, imageField } from "@web/views/fields/image/image_field";

export class PartnerImageField extends ImageField {
    static template = "web.PartnerImageField";

    get containsValidImage() {
        return this.props.record.data[this.props.name] && this.state.isValid;
    }

    get imgClass() {
        return super.imgClass + " border-0";
    }
}

export const partnerImageField = {
    ...imageField,
    component: PartnerImageField,
};

registry.category("fields").add("partner_image", partnerImageField);
