/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            followerListMenu
        [Element/model]
            ChatterTopbarComponent
        [Field/target]
            FollowerListMenuComponent
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
        [FollowerListMenuComponent/isDisabled]
            @record
            .{ChatterTopbarComponent/chatter}
            .{Chatter/isDisabled}
        [FollowerListMenuComponent/thread]
            @record
            .{ChatterTopbarComponent/chatter}
            .{Chatter/thread}
        [web.Element/style]
            [web.scss/display]
                flex
`;
