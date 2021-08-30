/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Determines all partners that are currently selected.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            selectedPartners
        [Field/model]
            ChannelInvitationForm
        [Field/type]
            many
        [Field/target]
            Partner
`;