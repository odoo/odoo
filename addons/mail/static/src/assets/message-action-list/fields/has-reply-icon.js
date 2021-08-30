/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Determines whether this message action list has a reply icon.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            hasReplyIcon
        [Field/model]
            MessageActionList
        [Field/type]
            attr
        [Field/target]
            Boolean
        [Field/compute]
            {Env/inbox}
            .{&}
                @record
                .{MessageActionList/message}
                .{Message/isTemporary}
                .{isFalsy}
            .{&}
                @record
                .{MessageActionList/message}
                .{Message/isTransient}
                .{isFalsy}
            .{&}
                @record
                .{MessageActionList/messageView}
            .{&}
                @record
                .{MessageActionList/messageView}
                .{MessageView/threadView}
            .{&}
                @record
                .{MessageActionList/messageView}
                .{MessageView/threadView}
                .{ThreadView/thread}
            .{&}
                @record
                .{MessageActionList/messageView}
                .{MessageView/threadView}
                .{ThreadView/thread}
                .{=}
                    {Env/inbox}
                .{|}
                    @record
                    .{MessageActionList/messageView}
                    .{MessageView/threadView}
                    .{ThreadView/thread}
                    .{Thread/model}
                    .{=}
                        mail.channel
`;
