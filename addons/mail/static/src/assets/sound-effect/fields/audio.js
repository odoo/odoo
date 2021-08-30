/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        HTMLAudioElement
        Does not require to be mounted on the DOM to operate.

        Set the first time the audio is played so the file is lazy loaded and
        then cached.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            audio
        [Field/model]
            SoundEffect
        [Field/type]
            attr
        [Field/target]
            Audio
`;
