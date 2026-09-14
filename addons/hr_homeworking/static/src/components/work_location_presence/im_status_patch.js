/** @odoo-module native */
import { patch } from "@web/core/utils/patch";

import { ImStatus } from "@mail/core/common/im_status";
import { ThreadIcon } from "@mail/core/common/thread_icon";
import { AvatarCardResourcePopover } from "@resource_mail/components/avatar_card_resource/avatar_card_resource_popover";
import { Store } from "@mail/core/common/store_service";

import {
    REACHABLE_WORK_LOCATION_STATUSES,
    workLocationPresence,
} from "@hr_homeworking/work_location_presence";

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

patch(Store.prototype, {
    get onlineMemberStatuses() {
        return [...super.onlineMemberStatuses, ...REACHABLE_WORK_LOCATION_STATUSES];
    },
});
