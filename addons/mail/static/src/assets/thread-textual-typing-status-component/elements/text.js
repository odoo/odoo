/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            text
        [Element/model]
            ThreadTextualTypingStatusComponent
        [web.Element/tag]
            span
        [web.Element/class]
            text-truncate
        [Element/isPresent]
            @record
            .{ThreadTextualTypingStatusComponent/thread}
            .{&}
                @record
                .{ThreadTextualTypingStatusComponent/thread}
                .{Thread/orderedOtherTypingMembers}
                .{Collection/length}
                .{>}
                    0
        [web.Element/textContent]
            @record
            .{ThreadTextualTypingStatusComponent/thread}
            .{Thread/typingStatusText}
`;
