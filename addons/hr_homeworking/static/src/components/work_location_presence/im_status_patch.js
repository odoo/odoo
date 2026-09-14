/** @odoo-module native */
import { patch } from "@web/core/utils/patch";

import { ImStatus } from "@mail/core/common/im_status";
import { ThreadIcon } from "@mail/core/common/thread_icon";
import { AvatarCardResourcePopover } from "@resource_mail/components/avatar_card_resource/avatar_card_resource_popover";

import { workLocationPresence } from "@hr_homeworking/work_location_presence";

patch(ImStatus.prototype, {
    get workLocation() {
        return workLocationPresence(this.persona?.im_status);
    },
});

patch(ThreadIcon.prototype, {
    get workLocation() {
        return workLocationPresence(this.correspondent?.im_status);
    },
});

patch(AvatarCardResourcePopover.prototype, {
    get workLocation() {
        return workLocationPresence(this.record?.im_status);
    },
});
