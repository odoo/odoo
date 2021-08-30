/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Determines whether 'this.thread' should be displayed.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            hasThreadView
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
            .{&}
                @record
                .{ChatWindow/isMemberListOpened}
                .{isFalsy}
            .{&}
                @record
                .{ChatWindow/channelInvitationForm}
                .{isFalsy}
`;
