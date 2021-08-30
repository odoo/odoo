/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        If set, this channel invitation form is content of related popover view.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            popoverViewOwner
        [Field/model]
            ChannelInvitationForm
        [Field/type]
            one
        [Field/target]
            PopoverView
        [Field/isReadonly]
            true
        [Field/isCausal]
            true
        [Field/inverse]
            PopoverView/channelInvitationForm
`;
