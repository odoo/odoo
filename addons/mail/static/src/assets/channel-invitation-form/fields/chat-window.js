/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            chatWindow
        [Field/model]
            ChannelInvitationForm
        [Field/type]
            one
        [Field/target]
            ChatWindow
        [Field/isReadonly]
            true
        [Field/inverse]
            ChatWindow/channelInvitationForm
`;