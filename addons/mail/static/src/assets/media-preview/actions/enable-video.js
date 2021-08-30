/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Asks for access to the user's video device if not granted yet, then
        starts recording and defines the resulting video stream as the source
        of the video element in order to display the video feedback.
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            MediaPreview/enableVideo
        [Action/params]
            record
                [type]
                    MediaPreview
        [Action/behavior]
            {if}
                @record
                .{MediaPreview/doesBrowserSupportMediaDevices}
                .{isFalsy}
            .{then}
                {break}
            {try}
                :videoStream
                    {MediaDevices/getUserMedia}
                        [0]
                            {web.Browser/navigator}
                            .{web.Navigator/mediaDevices}
                        [1]
                            [video]
                                true
                {Record/update}
                    [0]
                        @record
                    [1]
                        [MediaPreview/videoStream]
                            @videoStream
                {Record/update}
                    [0]
                        @record
                        .{MediaPreview/videoRef}
                    [1]
                        [web.Element/srcObject]
                            @record
                            .{MediaPreview/videoStream}
            .{catch}
                {Dev/comment}
                    TODO: display popup asking the user to re-enable their camera
`;
