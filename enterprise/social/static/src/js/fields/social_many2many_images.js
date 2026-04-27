/** @odoo-module **/

import { ImagesCarouselDialog } from "../images_carousel_dialog";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { Component } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";

/**
 * Component for a many2many field to <ir.attachment>, containing only images.
 */
export class SocialMany2manyImages extends Component {
    static template = "social.SocialMany2manyImages";
    static props = standardFieldProps;

    setup() {
        super.setup();
        this.dialog = useService("dialog");
    }

    get attachmentsIds() {
        return this.props.record.data[this.props.name].records.map((record) => record.resId);
    }

    onClickMoreImages() {
        this.dialog.add(ImagesCarouselDialog, {
            title: _t("Post Images"),
            activeIndex: 0,
            images: this.attachmentsIds.map((attachmentId) => `/web/image/${attachmentId}`),
        });
    }
}

export const socialMany2manyImages = {
    component: SocialMany2manyImages,
    supportedTypes: ["many2many"],
};

registry.category("fields").add("social_many2many_images", socialMany2manyImages);
