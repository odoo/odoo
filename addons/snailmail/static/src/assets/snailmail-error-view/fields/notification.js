/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Messages from snailmail are considered to have at most one notification.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            notification
        [Field/model]
            SnailmailErrorView
        [Field/type]
            type
        [Field/target]
            Notification
        [Field/isRequired]
            true
        [Field/compute]
            @record
            .{SnailmailErrorView/message}
            .{Message/notifications}
            .{Collection/first}
`;
