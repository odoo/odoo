/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Called to unregister an other member partner that is no longer typing
        something.
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            Thread/unregisterOtherMemberTypingMember
        [Action/params]
            thread
                [type]
                    Thread
            partner
                [type]
                    Partner
        [Action/behavior]
            :partnerTimer
                @thread
                .{Thread/_otherMembersLongTypingTimers}
                .{Collection/find}
                    {Record/insert}
                        [Record/models]
                            Function
                        [Function/in]
                            item
                        [Function/out]
                            @item
                            .{Timer/partner}
                            .{=}
                                @partner
            {Record/update}
                [0]
                    @thread
                [1]
                    [Thread/_otherMembersLongTypingTimers]
                        {Field/remove}
                            @partnerTimer
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
                                @partner
                                .{Record/id}
            {Record/update}
                [0]
                    @thread
                [1]
                    [Thread/orderedTypingMemberLocalIds]
                        @newOrderedTypingMemberLocalIds
                    [Thread/typingMembers]
                        {Field/remove}
                            @partner
`;
