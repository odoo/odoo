/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        States all partners that are potential choices according to this
        search term.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            selectablePartners
        [Field/model]
            ChannelInvitationForm
        [Field/type]
            many
        [Field/target]
            Partner
`;