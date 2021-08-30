/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            messageAuthorPrefix
        [Element/model]
            ThreadPreviewComponent
        [Field/target]
            MessageAuthorPrefixComponent
        [Element/isPresent]
            @record
            .{ThreadPreviewComponent/threadPreviewView}
            .{ThreadPreviewView/thread}
            .{Thread/lastMessage}
            .{&}
                @record
                .{ThreadPreviewComponent/threadPreviewView}
                .{ThreadPreviewView/thread}
                .{Thread/lastMessage}
                .{Message/author}
        [MessageAuthorPrefixComponent/message]
            @record
            .{ThreadPreviewComponent/threadPreviewView}
            .{ThreadPreviewView/thread}
            .{Thread/lastMessage}
        [MessageAuthorPrefixComponent/thread]
            @record
            .{ThreadPreviewComponent/threadPreviewView}
            .{ThreadPreviewView/thread}
`;
