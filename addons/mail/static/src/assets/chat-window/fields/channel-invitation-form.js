/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Determines the channel invitation form displayed by this chat window
        (if any). Only makes sense if hasInviteFeature is true.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            channelInvitationForm
        [Field/model]
            ChatWindow
        [Field/type]
            one
        [Field/target]
            ChannelInvitationForm
        [Field/isCausal]
            true
        [Field/inverse]
            ChannelInvitationForm/chatWindow
`;
