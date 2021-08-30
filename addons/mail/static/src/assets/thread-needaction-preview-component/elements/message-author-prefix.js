/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            messageAuthorPrefix
        [Element/model]
            ThreadNeedactionPreviewComponent
        [Field/target]
            MessageAuthorPrefixComponent
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
                .{Message/author}
        [MessageAuthorPrefixComponent/message]
            @record
            .{ThreadNeedactionPreviewComponent/threadNeedactionPreviewView}
            .{ThreadNeedactionPreviewView/thread}
            .{Thread/lastNeedactionMessageAsOriginThread}
        [MessageAuthorPrefixComponent/thread]
            @record
            .{ThreadNeedactionPreviewComponent/threadNeedactionPreviewView}
            .{ThreadNeedactionPreviewView/thread}
`;
