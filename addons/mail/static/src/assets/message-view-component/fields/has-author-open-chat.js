/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Determines whether author open chat feature is enabled on message.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            hasAuthorOpenChat
        [Field/model]
            MessageViewComponent
        [Field/type]
            attr
        [Field/target]
            Boolean
        [Field/compute]
            {if}
                {Env/currentGuest}
            .{then}
                false
            .{elif}
                @record
                .{MessageViewComponent/messageView}
                .{MessageView/message}
                .{Message/author}
                .{isFalsy}
            .{then}
                false
            .{elif}
                @record
                .{MessageViewComponent/threadView}
                .{&}
                    @record
                    .{MessageViewComponent/threadView}
                    .{ThreadView/thread}
                .{&}
                    @record
                    .{MessageViewComponent/threadView}
                    .{ThreadView/thread}
                    .{Thread/correspondent}
                    .{=}
                        @record
                        .{MessageViewComponent/messageView}
                        .{MessageView/message}
                        .{Message/author}
            .{then}
                false
            .{else}
                true
`;
