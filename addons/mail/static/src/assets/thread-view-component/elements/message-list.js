/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            messageList
        [Element/model]
            ThreadViewComponent
        [Field/target]
            MessageListComponent
        [Element/isPresent]
            .{ThreadViewComponent/threadView}
            .{ThreadView/messageListView}
        [MessageListComponent/getScrollableElement]
            @record
            .{ThreadViewComponent/getScrollableElement}
        [MessageListComponent/hasScrollAdjust]
            @record
            .{ThreadViewComponent/hasScrollAdjust}
        [MessageListComponent/selectedMessage]
            @record
            .{ThreadViewComponent/selectedMessage}
        [MessageListComponent/messageListView]
            @record
            .{ThreadViewComponent/threadView}
            .{ThreadView/messageListView}
        [web.Element/style]
            [web.scss/flex]
                1
                1
                auto
`;
