/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            MediaMonitoring/_getFrequencyIndex
        [Action/params]
            targetFrequency
                [type]
                    Number
                [description]
                    in Hz
            sampleRate
                [type]
                    Number
                [description]
                    the sample rate of the audio
            binCount
                [type]
                    Number
                [description]
                    AnalyserNode.frequencyBinCount
        [Action/returns]
            Number
                [description]
                    the index of the targetFrequency within binCount
        [Action/behavior]
            :index
                {Math/round}
                    @targetFrequency
                    .{/}
                        @sampleRate
                        .{/}
                            2
                    .{*}
                        @binCount
            {Math/min}
                [0]
                    {Math/max}
                        0
                        @index
                [1]
                    @binCount
`;
