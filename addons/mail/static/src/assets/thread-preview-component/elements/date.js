/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            date
        [Element/model]
            ThreadPreviewComponent
        [web.Element/tag]
            span
        [Record/models]
            NotificationListItemComponent/date
        [Element/isPresent]
            @record
            .{ThreadPreviewComponent/threadPreviewView}
            .{ThreadPreviewView/thread}
            .{Thread/lastMessage}
            .{&}
                @record
                .{ThreadPreviewComponent/threadPreviewView}
                .{ThreadPreviewView/thread}
                .{Thread/lastMessage}
                .{Message/date}
        [web.Element/textContent]
            @record
            .{ThreadPreviewComponent/threadPreviewView}
            .{ThreadPreviewView/thread}
            .{Thread/lastMessage}
            .{Message/date}
            .{Moment/fromNow}
`;
