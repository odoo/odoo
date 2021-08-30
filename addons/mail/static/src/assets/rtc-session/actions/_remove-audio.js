/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        cleanly removes the audio stream of the session
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            RtcSession/_removeAudio
        [Action/params]
            record
                [type]
                    RtcSession
        [Action/behavior]
            {if}
                @record
                .{RtcSession/audioStream}
            .{then}
                {foreach}
                    {AudioStream/getTracks}
                        @record
                        .{RtcSession/audioStream}
                .{as}
                    track
                .{do}
                    {Track/stop}
                        @track
            {if}
                @record
                .{RtcSession/audioElement}
            .{then}
                {Audio/pause}
                    @record
                    .{RtcSession/audioElement}
                {try}
                    {Record/update}
                        [0]
                            @record
                            .{RtcSession/audioElement}
                        [1]
                            [Audio/srcObject]
                                {Record/empty}
                .{catch}
                    {Dev/comment}
                        ignore error during remove, the value will be overwritten at next usage anyway
            {Record/update}
                [0]
                    @record
                [1]
                    [RtcSession/audioStream]
                        {Record/empty}
                    [RtcSession/isAudioInError]
                        false
`;
