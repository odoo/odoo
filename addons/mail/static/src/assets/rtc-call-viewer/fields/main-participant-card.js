/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        If set, the card to be displayed as the "main/spotlight" card.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            mainParticipantCard
        [Field/model]
            RtcCallViewer
        [Field/type]
            one
        [Field/target]
            RtcCallParticipantCard
        [Field/inverse]
            RtcCallParticipantCard/rtcCallViewerOfMainCard
        [Field/compute]
            {if}
                @record
                .{RtcCallViewer/threadView}
                .{isFalsy}
            .{then}
                {Record/empty}
            .{elif}
                {Env/focusedRtcSession}
                .{&}
                    {Env/focusedRtcSession}
                    .{RtcSession/channel}
                    .{=}
                        @record
                        .{RtcCallViewer/threadView}
                        .{ThreadView/thread}
            .{then}
                {Record/insert}
                    [Record/models]
                        RtcCallParticipantCard
                    [RtcCallParticipantCard/relationalId]
                        rtc_session_
                        .{+}
                            {Env/focusedRtcSession}
                            .{Record/id}
                        .{+}
                            _
                        .{+}
                            @record
                            .{RtcCallViewer/threadView}
                            .{ThreadView/thread}
                            .{Record/id}
                    [RtcCallParticipantCard/rtcSession]
                        {Env/focusedRtcSession}
                    [RtcCallParticipantCard/channel]
                        @record
                        .{RtcCallViewer/threadView}
                        .{ThreadView/thread}
            .{else}
                {Record/empty}
`;
