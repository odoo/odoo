/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Determines if the user is deafened, which means that all incoming
        audio tracks are disabled.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            isDeaf
        [Field/model]
            RtcSession
        [Field/type]
            attr
        [Field/target]
            Boolean
        [Field/default]
            false
`;
