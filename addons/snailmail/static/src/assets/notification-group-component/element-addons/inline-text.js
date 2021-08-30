/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            ElementAddon
        [ElementAddon/element]
            NotificationGroupComponent/inlineText
        [ElementAddon/feature]
            snailmail
        [ElementAddon/textContent]
            {if}
                @record
                .{NotificationGroupComponent/notificationGroupView}
                .{NotificationGroupView/notificationGroup}
                .{NotificationGroup/type}
                .{=}
                    snail
            .{then}
                {Locale/text}
                    An error occurred when sending a letter with Snailmail.
            .{else}
                @original
`;
