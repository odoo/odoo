/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            loadingMore
        [Element/model]
            MessageListComponent
        [Record/models]
            MessageListComponent/item
        [Element/isPresent]
            @record
            .{MessageListComponent/messageListView}
            .{MessageListView/threadViewOwner}
            .{ThreadView/threadCache}
            .{ThreadCache/isLoadingMore}
        [web.Element/style]
            [web.scss/align-self]
                center
`;
