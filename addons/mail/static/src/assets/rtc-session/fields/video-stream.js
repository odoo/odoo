/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        MediaStream of the user's video.

        Should be divided into userVideoStream and displayStream,
        once we allow both share and cam feeds simultaneously.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            videoStream
        [Field/model]
            RtcSession
        [Field/type]
            attr
        [Field/target]
            MediaStream
`;
