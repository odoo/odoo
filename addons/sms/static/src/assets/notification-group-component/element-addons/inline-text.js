/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            ElementAddon
        [ElementAddon/element]
            NotificationGroupComponent/inlineText
        [ElementAddon/feature]
            sms
        [ElementAddon/textContent]
            {if}
                @record
                .{NotificationGroupComponent/notificationView}
                .{NotificationGroupView/notificationGroup}
                .{NotificationGroup/type}
                .{=}
                    sms
            .{then}
                {Locale/text}
                    An error occurred when sending an SMS.
            .{else}
                @original
`;
