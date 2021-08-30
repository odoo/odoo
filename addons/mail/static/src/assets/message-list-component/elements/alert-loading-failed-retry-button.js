/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            alertLoadingFailedRetryButton
        [Element/model]
            MessageListComponent
        [web.Element/tag]
            button
        [web.Element/class]
            btn
            btn-link
        [Element/onClick]
            {if}
                @record
                .{MessageListComponent/messageListView}
                .{MessageListView/threadViewOwner}
                .{isFalsy}
            .{then}
                {break}
            {if}
                @record
                .{MessageListComponent/messageListView}
                .{MessageListView/threadViewOwner}
                .{ThreadView/threadCache}
                .{isFalsy}
            .{then}
                {break}
            {Record/update}
                [0]
                    @record
                    .{MessageListComponent/messageListView}
                    .{MessageListView/threadViewOwner}
                    .{ThreadView/threadCache}
                [1]
                    [ThreadCache/hasLoadingFailed]
                        false
            {MessageListComponent/_loadMore}
                @record
        [web.Element/textContent]
            {Locale/text}
                Click here to retry
`;
