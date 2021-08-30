/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            Rtc/_setDeafState
        [Action/params]
            isDeaf
                [type]
                    Boolean
        [Action/behavior]
            {RtcSession/updateAndBroadcast}
                [0]
                    {Rtc/currentRtcSession}
                [1]
                    [isDeaf]
                        @isDeaf
            {foreach}
                {Record/all}
                    [Record/models]
                        RtcSession
            .{as}
                session
            .{do}
                {if}
                    @session
                    .{RtcSession/audioElement}
                    .{isFalsy}
                .{then}
                    {continue}
                {Record/update}
                    [0]
                        @session
                        .{RtcSession/audioElement}
                    [1]
                        [Audio/muted]
                            @isDeaf
            {Rtc/_updateLocalAudioTrackEnabledState}
`;
