/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            onChange
        [onChange/name]
            onChangeNotifications
        [onChange/model]
            NotificationGroup
        [onChange/dependencies]
            NotificationGroup/notifications
        [onChange/behavior]
            {if}
                @record
                .{NotificationGroup/notifications}
                .{Collection/length}
                .{=}
                    0
            .{then}
                {Record/delete}
                    @record
`;
