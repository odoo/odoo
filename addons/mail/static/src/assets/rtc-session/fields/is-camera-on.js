/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Determines if the user is broadcasting a video from a user device (camera).
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            isCameraOn
        [Field/model]
            RtcSession
        [Field/type]
            attr
        [Field/target]
            Boolean
        [Field/default]
            false
`;
