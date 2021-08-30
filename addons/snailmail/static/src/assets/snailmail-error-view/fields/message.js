/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            message
        [Field/model]
            SnailmailErrorView
        [Field/type]
            type
        [Field/target]
            Message
        [Field/isRequired]
            true
        [Field/compute]
            @record
            .{SnailmailErrorView/dialogOwner}
            .{Dialog/messageViewOwnerAsSnailmailError}
            .{MessageView/message}
`;
