
import { registry } from "@web/core/registry";
import { ImageField, imageField } from '@web/views/fields/image/image_field';


export class PartnerImageField extends ImageField {
    static template = "web.PartnerImageField";
}

export const partnerImageField = {
    ...imageField,
    component: PartnerImageField,
};

registry.category("fields").add("partner_image", partnerImageField);
