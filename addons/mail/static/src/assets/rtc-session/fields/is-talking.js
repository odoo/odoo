/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Determines if the user is currently talking, which is based on
        voice activation or push to talk.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            isTalking
        [Field/model]
            RtcSession
        [Field/type]
            attr
        [Field/target]
            Boolean
        [Field/default]
            false
`;
