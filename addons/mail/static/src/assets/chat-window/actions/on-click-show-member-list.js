/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            ChatWindow/onClickShowMemberList
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
                    ChatWindow/onClickShowMemberList
            {Record/update}
                [0]
                    @chatWindow
                [1]
                    [ChatWindow/channelInvitationForm]
                        {Record/empty}
                    [ChatWindow/isMemberListOpened]
                        true
`;
