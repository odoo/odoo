/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            partnerImStatusIcon
        [Element/model]
            ThreadNeedactionPreviewComponent
        [Field/target]
            PartnerImStatusIconComponent
        [Record/models]
            NotificationListItemComponent/partnerImStatusIcon
        [Element/isPresent]
            @record
            .{ThreadNeedactionPreviewComponent/threadNeedactionPreviewView}
            .{ThreadNeedactionPreviewView/thread}
            .{Thread/correspondent}
            .{&}
                @record
                .{ThreadNeedactionPreviewComponent/threadNeedactionPreviewView}
                .{ThreadNeedactionPreviewView/thread}
                .{Thread/correspondent}
                .{Partner/imStatus}
        [PartnerImStatusIconComponent/partner]
            @record
            .{ThreadNeedactionPreviewComponent/threadNeedactionPreviewView}
            .{ThreadNeedactionPreviewView/thread}
            .{Thread/correspondent}
`;
