/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Iterates tracks of the provided MediaStream, calling the 'stop'
        method on each of them.
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            MediaPreview/stopTracksOnMediaStream
        [Action/params]
            mediaStream
                [type]
                    MediaStream
        [Action/behavior]
            {foreach}
                {MediaStream/getTracks}
                    @mediaStream
            .{as}
                track
            .{do}
                {MediaStreamTrack/stop}
                    @track
`;
