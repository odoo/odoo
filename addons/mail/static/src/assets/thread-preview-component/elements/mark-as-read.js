/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            markAsRead
        [Element/model]
            ThreadPreviewComponent
        [web.Element/tag]
            span
        [Record/models]
            ThreadPreviewComponent/coreItem
            NotificationListItemComponent/markAsRead
        [web.Element/class]
            fa
            fa-check
        [Element/isPresent]
            @record
            .{ThreadPreviewComponent/threadPreviewView}
            .{ThreadPreviewView/thread}
            .{Thread/localMessageUnreadCounter}
            .{>}
                0
        [web.Element/title]
            {Locale/text}
                Mark as Read
        [Element/onClick]
            {if}
                @record
                .{ThreadPreviewComponent/threadPreviewView}
                .{ThreadPreviewView/thread}
                .{Thread/lastMessage}
            .{then}
                {Thread/markAsSeen}
                    [0]
                        @record
                        .{ThreadPreviewComponent/threadPreviewView}
                        .{ThreadPreviewView/thread}
                    [1]
                        @record
                        .{ThreadPreviewComponent/threadPreviewView}
                        .{ThreadPreviewView/thread}
                        .{Thread/lastNonTransientMessage}
`;
