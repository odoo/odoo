/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            emptyStarredTitle
        [Element/model]
            MessageListComponent
        [Record/models]
            MessageListComponent/emptyTitle
        [Element/isPresent]
            @record
            .{MessageListComponent/messageListView}
            .{MessageListView/threadViewOwner}
            .{ThreadView/thread}
            .{=}
                {Env/starred}
        [web.Element/textContent]
            {Locale/text}
                No starred messages
`;
