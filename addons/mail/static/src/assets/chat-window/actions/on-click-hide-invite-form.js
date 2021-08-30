/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Handles click on the "stop adding users" button.
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            ChatWindow/onClickHideInviteForm
        [Action/params]
            chatWindow
                [type]
                    ChatWindow
            ev
                [type]
                    MouseEvent
        [Action/behavior]
            {Event/markAsHandled}
                [0]
                    @ev
                [1]
                    ChatWindow/onClickCommand
            {Record/update}
                [0]
                    @record
                [1]
                    [ChatWindow/channelInvitationForm]
                        {Record/empty}
`;
