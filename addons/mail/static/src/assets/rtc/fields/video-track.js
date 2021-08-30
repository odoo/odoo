/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        video MediaStreamTrack of the current user
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            videoTrack
        [Field/model]
            Rtc
        [Field/type]
            attr
        [Field/target]
            MediaStreamTrack
`;
