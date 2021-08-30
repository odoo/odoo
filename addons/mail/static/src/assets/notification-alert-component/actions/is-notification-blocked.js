/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            NotificationAlertComponent/isNotificationBlocked
        [Action/returns]
            Boolean
        [Action/behavior]
            {web.Browser/Notification}
            .{&}
                {web.Browser/Notification}
                .{!=}
                    granted
            .{&}
                {Env/isNotificationPermissionDefault}
                .{isFalsy}
`;
