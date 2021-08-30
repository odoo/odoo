/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        monitors the activity of an audio mediaStreamTrack
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            MediaMonitoring/monitorAudio
        [Action/params]
            track
                [type]
                    MediaStreamTrack
            processorOptions
                [type]
                    Object
                [description]
                    @param {Object} [processorOptions] options for the audio
                      processor
                    @param {Array<number>} [processorOptions.frequencyRange]
                      the range of frequencies to monitor in hz
                    @param {number} [processorOptions.minimumActiveCycles]
                      how many cycles have to pass since the last time the
                      threshold was exceeded to go back to inactive state,
                      this prevents stuttering when the speech volume oscillates
                      around the threshold value.
                    @param {function(boolean):void} [processorOptions.onThreshold]
                      a function to be called when the threshold is passed
                    @param {function(number):void} [processorOptions]
                      a function to be called at each tics
                    @param {number} [processorOptions.volumeThreshold]
                      the normalized minimum value for audio detection
        [Action/returns]
            Function
                [description]
                    @returns {function} callback to cleanly end the monitoring
        [Action/behavior]
            {Dev/comment}
                cloning the track so it is not affected by the enabled change of
                the original track.
            :monitoredTrack
                {MediaStreamTrack/clone}
                    @track
            {Record/update}
                [0]
                    monitoredTrack
                [1]
                    [MediaStreamTrack/enabled]
                        true
            :stream
                {Record/insert}
                    [Record/models]
                        MediaStream
                    @monitoredTrack
            :AudioContext
                {web.Browser/AudioContext}
                .{|}
                    {web.Browser/webkitAudioContext}
            {if}
                @AudioContext
                .{isFalsy}
            .{then}
                {Error/raise}
                    missing audio context
            :audioContext
                {Record/insert}
                    [Record/models]
                        AudioContext
            :source
                {AudioContext/createMediaStreamSource}
                    [0]
                        @audioContext
                    [1]
                        @stream
            {try}
                :processor
                    {MediaMonitoring/_loadAudioWorkletProcessor}
                        [0]
                            @source
                        [1]
                            @audioContext
                        [2]
                            @processorOptions
            .{catch}
                {Record/insert}
                    [Record/models]
                        Function
                    [Function/in]
                        error
                    [Function/out]
                        {Dev/comment}
                            In case Worklets are not supported by the browser
                            (eg: Safari)
                        :processor
                            {MediaMonitoring/_loadScriptProcessor}
                                [0]
                                    @source
                                [1]
                                    @audioContext
                                [2]
                                    @processorOptions
            {Record/insert}
                [Record/models]
                    Function
                [Function/out]
                    {Processor/disconnect}
                        @processor
                    {Source/disconnect}
                        @source
                    {MediaStreamTrack/stop}
                        @monitoredTrack
`;
