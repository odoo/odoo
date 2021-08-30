/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        The name of the rtcSession or the invited partner.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            name
        [Field/model]
            RtcCallParticipantCard
        [Field/type]
            attr
        [Field/target]
            String
        [Field/default]
            {Locale/text}
                Anonymous
        [Field/compute]
            {if}
                @record
                .{RtcCallParticipantCard/rtcSession}
            .{then}
                @record
                .{RtcCallParticipantCard/rtcSession}
                .{RtcSession/name}
            .{elif}
                @record
                .{RtcCallParticipantCard/invitedPartner}
            .{then}
                @record
                .{RtcCallParticipantCard/invitedPartner}
                .{Partner/name}
            .{elif}
                @record
                .{RtcCallParticipantCard/invitedGuest}
            .{then}
                @record
                .{RtcCallParticipantCard/invitedGuest}
                .{Guest/name}
`;
