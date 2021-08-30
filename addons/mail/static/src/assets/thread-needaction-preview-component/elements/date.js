/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            date
        [Element/model]
            ThreadNeedactionPreviewComponent
        [web.Element/tag]
            span
        [Record/models]
            NotificationListItemComponent/date
        [Element/isPresent]
            @record
            .{ThreadNeedactionPreviewComponent/threadNeedactionPreviewView}
            .{ThreadNeedactionPreviewView/thread}
            .{Thread/lastNeedactionMessageAsOriginThread}
            .{&}
                @record
                .{ThreadNeedactionPreviewComponent/threadNeedactionPreviewView}
                .{ThreadNeedactionPreviewView/thread}
                .{Thread/lastNeedactionMessageAsOriginThread}
                .{Message/date}
        [web.Element/textContent]
            @record
            .{ThreadNeedactionPreviewComponent/threadNeedactionPreviewView}
            .{ThreadNeedactionPreviewView/thread}
            .{Thread/lastNeedactionMessageAsOriginThread}
            .{Message/date}
            .{Moment/fromNow}
`;
