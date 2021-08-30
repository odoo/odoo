/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        callback to properly end the audio monitoring.
        If set it indicates that we are currently monitoring the local
        audioTrack for the voice activation feature.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            disconnectAudioMonitor
        [Field/model]
            Rtc
        [Field/type]
            attr
        [Field/target]
            Function
`;
