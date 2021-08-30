/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            emptyHistoryTitle
        [Element/model]
            MessageListComponent
        [Record/models]
            MessageListComponent/emptyTitle
        [web.Element/class]
            o-neutral-face-icon
        [Element/isPresent]
            @record
            .{MessageListComponent/messageListView}
            .{MessageListView/threadViewOwner}
            .{ThreadView/thread}
            .{=}
                {Env/history}
        [web.Element/textContent]
            {Locale/text}
                No history messages
`;
