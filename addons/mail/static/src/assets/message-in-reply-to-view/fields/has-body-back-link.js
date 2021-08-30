/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Determines if the reply has a back link to a non-empty body.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            hasBodyBackLink
        [Field/model]
            MessageInReplyToView
        [Field/type]
            attr
        [Field/target]
            Boolean
        [Field/compute]
            @record
            .{MessageInReplyToView/messageView}
            .{MessageView/message}
            .{Message/parentMessage}
            .{Message/isBodyEmpty}
            .{isFalsy}
`;
