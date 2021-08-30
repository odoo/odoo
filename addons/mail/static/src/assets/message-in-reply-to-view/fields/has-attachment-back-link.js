/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Determines if the reply has a back link to an attachment only
        message.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            hasAttachmentBackLink
        [Field/model]
            MessageInReplyToView
        [Field/type]
            attr
        [Field/target]
            Boolean
        [Field/compute]
            :parentMessage
                @record
                .{MessageInReplyToView/messageView}
                .{MessageView/message}
                .{Message/parentMessage}
            @parentMessage
            .{Message/isBodyEmpty}
            .{&}
                @parentMessage
                .{Message/hasAttachments}
`;
