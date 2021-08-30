/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Resets the audio to the start of the track and pauses it.
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            SoundEffect/stop
        [Action/params]
            record
                [type]
                    SoundEffect
        [Action/behavior]
            {if}
                @record
                .{SoundEffect/audio}
            .{then}
                {Audio/pause}
                    @record
                    .{SoundEffect/audio}
                {Record/update}
                    [0]
                        @record
                        .{SoundEffect/audio}
                    [1]
                        [Audio/currentTime]
                            0
`;
