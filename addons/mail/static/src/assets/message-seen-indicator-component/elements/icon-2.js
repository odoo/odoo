/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            icon2
        [Element/model]
            MessageSeenIndicatorComponent
        [web.Element/tag]
            i
        [Record/models]
            MessageSeenIndicatorComponent/icon
        [web.Element/class]
            fa
            fa-check
        [Element/isPresent]
            @record
            .{MessageSeenIndicatorComponent/messageSeenIndicator}
            .{MessageSeenIndicator/isMessagePreviousToLastCurrentPartnerMessageSeenByEveryone}
            .{isFalsy}
            .{&}
                @record
                .{MessageSeenIndicatorComponent/messageSeenIndicator}
                .{MessageSeenIndicator/hasSomeoneSeen}
        [web.Element/style]
            [web.scss/position]
                absolute
            [web.scss/top]
                -1px
            [web.scss/left]
                -1px
`;
