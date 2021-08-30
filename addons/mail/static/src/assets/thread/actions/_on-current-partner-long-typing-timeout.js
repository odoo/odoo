/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Called when current partner has been typing for a very long time.
        Immediately notify other members that he/she is still typing.
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            Thread/_onCurrentPartnerLongTypingTimeout
        [Action/params]
            thread
                [type]
                    Thread
        [Action/behavior]
            {Record/update}
                [0]
                    @thread
                [1]
                    [Thread/_forceNotifyNextCurrentPartnerTypingStatus]
                        true
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
                                true
`;
