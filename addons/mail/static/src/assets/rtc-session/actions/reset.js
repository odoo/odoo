/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        restores the session to its default values
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            RtcSession/reset
        [Action/params]
            record
                [type]
                    RtcSession
        [Action/behavior]
            {if}
                @record
                .{RtcSession/_timeoutId}
            .{then}
                {Browser/clearTimeout}
                    @record
                    .{RtcSession/_timeoutId}
            {RtcSession/_removeAudio}
                @record
            {RtcSession/_removeVideo}
                @record
            {Record/update}
                [0]
                    @record
                [1]
                    [RtcSession/audioElement]
                        {Record/empty}
                    [RtcSession/isTalking]
                        {Record/empty}
`;
