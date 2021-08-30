/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            icon1
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
                .{MessageSeenIndicator/hasSomeoneFetched}
                .{|}
                    @record
                    .{MessageSeenIndicatorComponent/messageSeenIndicator}
                    .{MessageSeenIndicator/hasSomeoneSeen}
        [web.Element/style]
            [web.scss/padding-left]
                {scss/map-get}
                    {scss/$spacers}
                    1

`;
