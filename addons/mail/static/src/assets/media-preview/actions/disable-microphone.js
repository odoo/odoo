/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Stops recording user's microphone.
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            MediaPreview/disableMicrophone
        [Action/params]
            record
                [type]
                    MediaPreview
        [Action/behavior]
            {Record/update}
                [0]
                    @record
                    .{MediaPreview/audioRef}
                [1]
                    [web.Element/srcObject]
                        null
            {if}
                @record
                .{MediaPreview/audioStream}
                .{isFalsy}
            .{then}
                {break}
            {MediaPreview/stopTracksOnMediaStream}
                @record
                .{MediaPreview/audioStream}
            {Record/update}
                [0]
                    @record
                [1]
                    [MediaPreview/audioStream]
                        null
`;
