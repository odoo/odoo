/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        If set, this card represents an invitation of this partner to this call.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            invitedPartner
        [Field/model]
            RtcCallParticipantCard
        [Field/type]
            one
        [Field/target]
            Partner
`;
