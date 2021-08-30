/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            buttonAttachmentsCount
        [Element/model]
            ChatterTopbarComponent
        [web.Element/tag]
            span
        [Record/models]
            ChatterTopbarComponent/buttonCount
        [Element/isPresent]
            @record
            .{ChatterTopbarComponent/chatter}
            .{Chatter/isShowingAttachmentsLoading}
            .{isFalsy}
        [web.Element/textContent]
            {if}
                @record
                .{ChatterTopbarComponent/chatter}
                .{Chatter/thread}
                .{isFalsy}
            .{then}
                0
            .{else}
                @record
                .{ChatterTopbarComponent/chatter}
                .{Chatter/thread}
                .{Thread/allAttachments}
                .{Collection/length}
`;
