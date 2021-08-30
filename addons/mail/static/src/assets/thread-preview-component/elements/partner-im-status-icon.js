/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            partnerImStatusIcon
        [Element/model]
            ThreadPreviewComponent
        [Field/target]
            PartnerImStatusIconComponent
        [Record/models]
            NotificationListItemComponent/partnerImStatusIcon
        [Element/isPresent]
            @record
            .{ThreadPreviewComponent/threadPreviewView}
            .{ThreadPreviewView/thread}
            .{Thread/correspondent}
            .{&}
                @record
                .{ThreadPreviewComponent/threadPreviewView}
                .{ThreadPreviewView/thread}
                .{Thread/correspondent}
                .{Partner/imStatus}
        [PartnerImStatusIconComponent/partner]
            @record
            .{ThreadPreviewComponent/threadPreviewView}
            .{ThreadPreviewView/thread}
            .{Thread/correspondent}
        [web.Element/style]
            {if}
                @record
                .{ThreadPreviewComponent/threadPreviewView}
                .{ThreadPreviewView/thread}
                .{Thread/localMessageUnreadCounter}
                .{=}
                    0
            .{then}
                [web.scss/color]
                    {scss/$o-mail-notification-list-item-muted-background-color}
`;
