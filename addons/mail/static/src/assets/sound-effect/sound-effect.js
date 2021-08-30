/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Model
        [Model/name]
            SoundEffect
        [Model/fields]
            audio
            defaultVolume
            filename
            path
        [Model/id]
            SoundEffect/path
            .{&}
                SoundEffect/filename
        [Model/actions]
            SoundEffect/play
            SoundEffect/stop
`;
