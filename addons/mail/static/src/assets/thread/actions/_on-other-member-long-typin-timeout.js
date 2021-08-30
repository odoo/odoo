/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            Thread/_onOtherMemberLongTypingTimeout
        [Action/params]
            thread
                [type]
                    Thread
            partner
                [type]
                    Partner
        [Action/behavior]
            {if}
                @thread
                .{Thread/typingMembers}
                .{Collection/includes}
                    @partner
                .{isFalsy}
            .{then}
                {Dev/comment}
                    AKU TODO: timer should not be coupled with partner
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
            .{then}
                {Thread/unregisterOtherMemberTypingMember}
                    [0]
                        @thread
                    [1]
                        @partner
`;
