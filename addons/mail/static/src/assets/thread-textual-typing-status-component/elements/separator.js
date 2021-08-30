/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            separator
        [Element/model]
            ThreadTextualTypingStatusComponent
        [web.Element/tag]
            span
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
        [web.Element/style]
            [web.scss/width]
                {scss/map-get}
                    {scss/$spacers}
                    1
`;
