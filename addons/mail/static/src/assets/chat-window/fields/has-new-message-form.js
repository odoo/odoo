/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Determines whether "new message form" should be displayed.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            hasNewMessageForm
        [Field/model]
            ChatWindow
        [Field/type]
            attr
        [Field/target]
            Boolean
        [Field/compute]
            @record
            .{ChatWindow/isVisible}
            .{&}
                @record
                .{ChatWindow/isFolded}
                .{isFalsy}
            .{&}
                @record
                .{ChatWindow/thread}
                .{isFalsy}
`;
