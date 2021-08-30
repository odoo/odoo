/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            alertLoadingFailed
        [Element/model]
            MessageListComponent
        [web.Element/class]
            alert
            alert-info
            d-flex
            align-items-center
        [Element/isPresent]
            @record
            .{MessageListComponent/messageListView}
            .{MessageListView/threadViewOwner}
            .{&}
                @record
                .{MessageListComponent/messageListView}
                .{MessageListView/threadViewOwner}
                .{ThreadView/threadCache}
                .{ThreadCache/hasLoadingFailed}
`;
