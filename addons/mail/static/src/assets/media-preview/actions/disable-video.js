/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Stops recording user's video device.
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            MediaPreview/disableVideo
        [Action/params]
            record
                [type]
                    MediaPreview
        [Action/behavior]
            {Record/update}
                [0]
                    @record
                    .{MediaPreview/videoRef}
                [1]
                    [web.Element/srcObject]
                        null
            {if}
                @record
                .{MediaPreview/videoStream}
                .{isFalsy}
            .{then}
                {break}
            {MediaPreview/stopTracksOnMediaStream}
                @record
                .{MediaPreview/videoStream}
            {Record/update}
                [0]
                    @record
                [1]
                    [MediaPreview/videoStream]
                        null
`;
