/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Called when current partner has explicitly stopped inserting some
        input in composer. Useful to notify current partner has currently
        stopped typing something in the composer of this thread to all other
        members.
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            Thread/unregisterCurrentPartnerIsTyping
        [Action/params]
            thread
                [type]
                    Thread
            immediateNotify
                [type]
                    Boolean
                [default]
                    false
                [description]
                    if set, is typing status of current partner is immediately
                    notified and doesn't consume throttling at all.
        [Action/behavior]
            {Dev/comment}
                Handling of typing timers.
            {Timer/clear}
                @thread
                .{Thread/_currentPartnerInactiveTypingTimer}
            {Timer/clear}
                @thread
                .{Thread/_currentPartnerLongTypingTimer}
            {Dev/comment}
                Manage typing member relation.
            :newOrderedTypingMemberLocalIds
                @thread
                .{Thread/orderedTypingMemberLocalIds}
                .{Collection/filter}
                    {Record/insert}
                        [Record/models]
                            Function
                        [Function/in]
                            item
                        [Function/out]
                            @item
                            .{!=}
                                {Env/currentPartner}
                                .{Record/id}
            {Record/update}
                [0]
                    @thread
                [1]
                    [Thread/orderedTypingMemberLocalIds]
                        @newOrderedTypingMemberLocalIds
                    [Thread/typingMembers]
                        {Field/remove}
                            {Env/currentPartner}
            {Dev/comment}
                Notify typing status to other members.
            {if}
                @immediateNotify
            .{then}
                {Throttle/clear}
                    @thread
                    .{Thread/_throttleNotifyCurrentPartnerTypingStatus}
            {Record/doAsync}
                [0]
                    @thread
                [1]
                    {Throttle/call}
                        [0]
                            @thread
                            .{Thread/_throttleNotifyCurrentPartnerTypingStatus}
                        [1]
                            [isTyping]
                                false
`;
