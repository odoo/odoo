/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Called when current partner is inserting some input in composer.
        Useful to notify current partner is currently typing something in the
        composer of this thread to all other members.
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            Thread/registerCurrentPartnerIsTyping
        [Action/params]
            thread
                [type]
                    Thread
        [Action/behavior]
            {Dev/comment}
                Handling of typing timers.
            {Timer/start}
                @thread
                .{Thread/_currentPartnerInactiveTypingTimer}
            {Timer/start}
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
            @newOrderedTypingMemberLocalIds
            .{Collection/push}
                {Env/currentPartner}
                .{Record/id}
            {Record/update}
                [0]
                    @thread
                [1]
                    [Thread/orderedTypingMemberLocalIds]
                        @newOrderedTypingMemberLocalIds
                    [Thread/typingMembers]
                        {Field/add}
                            {Env/currentPartner}
            {Dev/comment}
                Notify typing status to other members.
            {Throttle/call}
                [0]
                    @thread
                    .{Thread/_throttleNotifyCurrentPartnerTypingStatus}
                [1]
                    [isTyping]
                        true
`;
