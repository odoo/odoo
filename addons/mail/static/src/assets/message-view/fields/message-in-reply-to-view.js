/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        States the message in reply to view that displays the message of
        which this message is a reply to (if any).
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            messageInReplyToView
        [Field/model]
            MessageView
        [Field/type]
            one
        [Field/target]
            MessageInReplyToView
        [Field/isCausal]
            true
        [Field/isReadonly]
            true
        [Field/inverse]
            MessageInReplyToView/messageView
        [Field/compute]
            {if}
                @record
                .{MessageView/message}
                .{&}
                    @record
                    .{MessageView/message}
                    .{Message/originThread}
                .{&}
                    @record
                    .{MessageView/message}
                    .{Message/originThread}
                    .{Thread/model}
                    .{=}
                        mail.channel
                .{&}
                    @record
                    .{MessageView/message}
                    .{Message/parentMessage}
            .{then}
                {Record/insert}
                    [Record/models]
                        MessageInReplyToView
            .{else}
                {Record/empty}
`;
