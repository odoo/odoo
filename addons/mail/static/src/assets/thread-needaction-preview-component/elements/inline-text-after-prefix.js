/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            inlineTextAfterPrefix
        [Element/model]
            ThreadNeedactionPreviewComponent
        [web.Element/tag]
            span
        [web.Element/textContent]
            {if}
                @record
                .{ThreadNeedactionPreviewComponent/threadNeedactionPreviewView}
                .{ThreadNeedactionPreviewView/thread}
                .{Thread/lastNeedactionMessageAsOriginThread}
            .{then}
                {Utils/htmlToTextContentInline}
                    @record
                    .{ThreadNeedactionPreviewComponent/threadNeedactionPreviewView}
                    .{ThreadNeedactionPreviewView/thread}
                    .{Thread/lastNeedactionMessageAsOriginThread}
                    .{Message/prettyBody}
`;
