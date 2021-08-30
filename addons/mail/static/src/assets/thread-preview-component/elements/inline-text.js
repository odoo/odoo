/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            inlineText
        [Element/model]
            ThreadPreviewComponent
        [web.Element/tag]
            span
        [Record/models]
            ThreadPreviewComponent/coreItem
            NotificationListItemComponent/inlineText
        [web.Element/style]
            {if}
                @record
                .{ThreadPreviewComponent/threadPreviewView}
                .{ThreadPreviewView/thread}
                .{Thread/lastMessage}
                .{isFalsy}
                .{|}
                    {Utils/htmlToTextContentInline}
                        @record
                        .{ThreadPreviewComponent/threadPreviewView}
                        .{ThreadPreviewView/thread}
                        .{Thread/lastMessage}
                        .{Message/prettyBody}
                    .{String/length}
                    .{=}
                        0
            .{then}
                {web.scss/selector}
                    [0]
                        &::before
                    [1]
                        {Dev/comment}
                            AKU TODO: FIXME
                        [web.scss/content]
                            {Char/noBreakSpace}
                            {Dev/comment}
                                keep line-height as if it had content
`;
