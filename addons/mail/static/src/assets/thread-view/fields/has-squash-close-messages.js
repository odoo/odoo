/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Determines whether this thread view should squash close messages.
        See '_shouldMessageBeSquashed' for which conditions are considered
        to determine if messages are "close" to each other.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            hasSquashCloseMessages
        [Field/model]
            ThreadView
        [Field/type]
            attr
        [Field/target]
            Boolean
        [Field/compute]
            @record
            .{ThreadView/threadViewer}
            .{&}
                @record
                .{ThreadView/threadViewer}
                .{ThreadViewer/chatter}
                .{isFalsy}
            .{&}
                @record
                .{ThreadView/thread}
            .{&}
                @record
                .{ThreadView/thread}
                .{Thread/model}
                .{!=}
                    mail.box
`;
