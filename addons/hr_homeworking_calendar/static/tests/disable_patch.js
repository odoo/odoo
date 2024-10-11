import {
        unpatchAttendeeCalendarCommonPopover,
        unpatchAttendeeCalendarCommonPopoverClass
    } from "@hr_homeworking_calendar/calendar/common/popover/calendar_common_popover";

import { unpatchAvatarCardResourcePopover } from "@hr/components/avatar_card_resource/avatar_card_resource_popover_patch";

unpatchAttendeeCalendarCommonPopover();
unpatchAttendeeCalendarCommonPopoverClass();
unpatchAvatarCardResourcePopover();
