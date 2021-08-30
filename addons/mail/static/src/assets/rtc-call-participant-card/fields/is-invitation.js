/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        States whether this card is representing a person with a pending
        invitation.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            isInvitation
        [Field/model]
            RtcCallParticipantCard
        [Field/type]
            attr
        [Field/target]
            Boolean
        [Field/compute]
            @record
            .{RtcCallParticipantCard/invitedPartner}
            .{|}
                @record
                .{RtcCallParticipantCard/invitedGuest}
`;
