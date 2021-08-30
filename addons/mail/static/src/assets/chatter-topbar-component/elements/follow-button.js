/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            followButton
        [Element/model]
            ChatterTopbarComponent
        [Field/target]
            FollowButtonComponent
        [Record/models]
            ChatterTopbarComponent/button
        [Element/isPresent]
            @record
            .{ChatterTopbarComponent/chatter}
            .{Chatter/hasFollowers}
            .{&}
                @record
                .{ChatterTopbarComponent/chatter}
                .{Chatter/thread}
            .{&}
                @record
                .{ChatterTopbarComponent/chatter}
                .{Chatter/thread}
                .{Thread/channelType}
                .{!=}
                    chat
        [FollowButtonComponent/isDisabled]
            @record
            .{ChatterTopbarComponent/chatter}
            .{Chatter/isDisabled}
        [FollowButtonComponent/thread]
            @record
            .{ChatterTopbarComponent/chatter}
            .{Chatter/thread}
`;
