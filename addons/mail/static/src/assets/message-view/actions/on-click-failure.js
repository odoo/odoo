/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            MessageView/onClickFailure
        [Action/params]
            record
                [type]
                    MessageView
            ev
                [type]
                    web.MouseEvent
        [Action/behavior]
            {Event/markAsHandled}
                [0]
                    @ev
                [1]
                    Message.ClickFailure
            {Message/openResendAction}
                @record
                .{MessageView/message}
`;
