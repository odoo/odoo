/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Handles click on the "add users" button.
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            ChatWindow/onClickShowInviteForm
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
                        {Record/insert}
                            [Record/models]
                                ChannelInvitationForm
                            [ChannelInvitationForm/doFocusOnSearchInput]
                                true
                    [ChatWindow/isMemberListOpened]
                        false
            {if}
                {Env/isCurrentUserGuest}
                .{isFalsy}
            .{then}
                {ChannelInvitationForm/searchPartnersToInvite}
                    @record
                    .{ChatWindow/channelInvitationForm}
`;
