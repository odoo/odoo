/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            channelMemberList
        [Element/model]
            ThreadViewComponent
        [Element/isPresent]
            @record
            .{ThreadViewComponent/threadView}
            .{ThreadView/thread}
            .{Thread/hasMemberListFeature}
            .{&}
                @record
                .{ThreadViewComponent/threadView}
                .{ThreadView/hasMemberList}
            .{&}
                @record
                .{ThreadViewComponent/threadView}
                .{ThreadView/isMemberListOpened}
        [web.Element/target]
            ChannelMemberListComponent
        [web.Element/class]
            flex-shrink-0
            border-left
        [ChannelMemberListComponent/channel]
            @record
            .{ThreadViewComponent/threadView}
            .{ThreadView/thread}
        [web.Element/style]
            [web.scss/width]
                {scss/$o-mail-chat-sidebar-width}
`;
