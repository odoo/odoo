/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Determines if the rtcSession is in a valid "talking" state.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            isTalking
        [Field/model]
            RtcCallParticipantCard
        [Field/type]
            attr
        [Field/target]
            Boolean
        [Field/default]
            False
        [Field/compute]
            @record
            .{RtcCallParticipantCard/rtcSession}
            .{&}
                @record
                .{RtcCallParticipantCard/rtcSession}
                .{RtcSession/isTalking}
            .{&}
                @record
                .{RtcCallParticipantCard/rtcSession}
                .{RtcSession/isMute}
                .{isFalsy}
`;
