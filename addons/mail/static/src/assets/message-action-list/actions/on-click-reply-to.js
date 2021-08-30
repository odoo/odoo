/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Opens the reply composer for this message (or closes it if it was
        already opened).
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            MessageActionList/onClickReplyTo
        [Action/params]
            ev
                [type]
                    MouseEvent
            record
                [type]
                    MessageActionList
        [Action/behavior]
            {Event/markAsHandled}
                [0]
                    @ev
                [1]
                    MessageActionList/onClickReplyTo
            {MessageView/replyTo}
                @record
                .{MessageActionList/messageView}
`;
