/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            authorNameStandard
        [Element/model]
            MessageViewComponent
        [Record/models]
            MessageViewComponent/authorName
            MessageViewComponent/authorRedirect
        [Element/isPresent]
            @record
            .{MessageViewComponent/messageView}
            .{MessageView/message}
            .{Message/author}
        [Element/onClick]
            {Event/markHandled}
                @ev
                MessageViewComponent.ClickAuthorName
            {if}
                @record
                .{MessageViewComponent/messageView}
                .{MessageView/message}
                .{Message/author}
            .{then}
                {Partner/openProfile}
                    @record
                    .{MessageViewComponent/messageView}
                    .{MessageView/message}
                    .{Message/author}
        [web.Element/title]
            {Locale/text}
                Open profile
        [web.Element/textContent]
            {if}
                @record
                .{MessageViewComponent/messageView}
                .{MessageView/message}
                .{Message/originThread}
            .{then}
                {Thread/getMemberName}
                    [0]
                        @record
                        .{MessageViewComponent/messageView}
                        .{MessageView/message}
                        .{Message/originThread}
                    [1]
                        @record
                        .{MessageViewComponent/messageView}
                        .{MessageView/message}
                        .{Message/author}
            .{else}
                @record
                .{MessageViewComponent/messageView}
                .{MessageView/message}
                .{Message/author}
                .{Author/nameOrDisplayName}
`;
