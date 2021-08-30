/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        HTMLAudioElement that plays and control the audioStream of the user,
        it is not mounted on the DOM as it can operate from the JS.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            audioElement
        [Field/model]
            RtcSession
        [Field/type]
            attr
        [Field/target]
            Audio
`;
