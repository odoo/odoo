/** @odoo-module native */
import { patch } from "@web/core/utils/patch";

import { AvatarCardResourcePopover } from "@resource_mail/components/avatar_card_resource/avatar_card_resource_popover";

import { workLocationPresence } from "@hr_homeworking/work_location_presence";

patch(AvatarCardResourcePopover.prototype, {
    get workLocation() {
        return workLocationPresence(this.record?.im_status);
    },
});
