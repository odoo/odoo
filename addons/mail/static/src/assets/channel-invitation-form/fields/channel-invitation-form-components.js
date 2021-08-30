/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        States the OWL components of this channel invitation form.
        Useful to be able to close them with popover trigger, or to know when
        they are open to update the button active state.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            channelInvitationFormComponents
        [Field/model]
            ChannelInvitationForm
        [Field/type]
            many
        [Field/target]
            ChannelInvitationFormComponent
        [Field/inverse]
            ChannelInvitationFormComponent/channelInvitationForm
`;