/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Called to refresh a registered other member partner that is typing
        something.
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            Thread/refreshOtherMemberTypingMember
        [Action/params]
            thread
                [type]
                    Thread
            partner
                [type]
                    Partner
        [Action/behavior]
            {Timer/reset}
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
`;
