/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Refresh the typing status of the current partner.
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            Thread/refreshCurrentPartnerIsTyping
        [Action/params]
            thread
                [type]
                    Thread
        [Action/behavior]
            {Timer/reset}
                @thread
                .{Thread/_currentPartnerInactiveTypingTimer}
`;
