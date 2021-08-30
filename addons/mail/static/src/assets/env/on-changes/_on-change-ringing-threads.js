/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            onChange
        [onChange/name]
            Env/_onChangeRingingThreads
        [onChange/model]
            Env
        [onChange/dependencies]
            Env/ringingThreads
        [onChange/behavior]
            {if}
                {Env/ringingThreads}
                .{&}
                    {Env/ringingThreads}
                    .{Collection/length}
                    .{>}
                        0
            .{then}
                {SoundEffect/play}
                    [0]
                        {SoundEffects/incomingCall}
                    [1]
                        [loop]
                            true
            .{else}
                {SoundEffect/stop}
                    {SoundEffect/incomingCall}
`;
