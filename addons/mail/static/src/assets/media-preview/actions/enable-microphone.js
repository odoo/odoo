/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Asks for access to the user's microphone if not granted yet, then
        starts recording and defines the resulting audio stream as the source
        of the audio element in order to play the audio feedback.
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            MediaPreview/enableMicrophone
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
                :audioStream
                    {MediaDevices/getUserMedia}
                        [0]
                            {web.Browser/navigator}
                            .{web.Navigator/mediaDevices}
                        [1]
                            [audio]
                                true
                {Record/update}
                    [0]
                        @record
                    [1]
                        [MediaPreview/audioStream]
                            @audioStream
                {Record/update}
                    [0]
                        @record
                        .{MediaPreview/audioRef}
                    [1]
                        [web.Element/srcObject]
                            @record
                            .{MediaPreview/audioStream}
            .{catch}
                {Dev/comment}
                    TODO: display popup asking the user to re-enable their mic
`;
