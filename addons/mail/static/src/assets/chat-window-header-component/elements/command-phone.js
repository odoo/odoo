/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            commandPhone
        [Element/model]
            ChatWindowHeaderComponent
        [Record/models]
            ChatWindowHeaderComponent/command
        [web.Element/isDisabled]
            @record
            .{ChatWindowHeaderComponent/chatWindow}
            .{ChatWindow/thread}
            .{Thread/hasPendingRtcRequest}
        [web.Element/title]
            {Locale/text}
                Start a Call
        [Element/onClick]
            {web.Event/stopPropagation}
                @ev
            {if}
                @record
                .{ChatWindowHeaderComponent/chatWindow}
                .{ChatWindow/thread}
                .{Thread/hasPendingRtcRequest}
            .{then}
                {break}
            {Thread/toggleCall}
                @record
                .{ChatWindowHeaderComponent/chatWindow}
                .{ChatWindow/thread}
`;
