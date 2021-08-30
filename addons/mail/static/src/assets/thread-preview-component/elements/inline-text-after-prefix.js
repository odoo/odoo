/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            inlineTextAfterPrefix
        [Element/model]
            ThreadPreviewComponent
        [web.Element/tag]
            span
        [web.Element/textContent]
            {if}
                @record
                .{ThreadPreviewComponent/threadPreviewView}
                .{ThreadPreviewView/thread}
                .{Thread/lastMessage}
            .{then}
                {Utils/htmlToTextContentInline}
                    @record
                    .{ThreadPreviewComponent/threadPreviewView}
                    .{ThreadPreviewView/thread}
                    .{Thread/lastMessage}
                    .{Message/prettyBody}
`;
