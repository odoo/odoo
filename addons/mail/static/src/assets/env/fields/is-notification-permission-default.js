/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        States whether browser Notification Permission is currently in its
        'default' state. This means it is allowed to make a request to the
        user to enable notifications.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            isNotificationPermissionDefault
        [Field/model]
            Env
        [Field/type]
            attr
        [Field/target]
            Boolean
        [Field/compute]
            {if}
                {web.Browser/Notification}
            .{then}
                false
            .{else}
                {web.Browser/Notification}
                .{web.Notification/permission}
                .{=}
                    default
`;
