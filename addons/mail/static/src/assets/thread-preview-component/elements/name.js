/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            name
        [Element/model]
            ThreadPreviewComponent
        [web.Element/tag]
            span
        [Record/models]
            {if}
                @record
                .{ThreadPreviewComponent/threadPreviewView}
                .{ThreadPreviewView/thread}
                .{Thread/localMessageUnreadCounter}
                .{>}
                    0
            .{then}
                NotificationListItemComponent/bold
            NotificationListItemComponent/name
        [web.Element/textContent]
            @record
            .{ThreadPreviewComponent/threadPreviewView}
            .{ThreadPreviewView/thread}
            .{Thread/displayName}
`;
