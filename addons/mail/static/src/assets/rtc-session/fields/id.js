/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Id of the record on the server.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            id
        [Field/model]
            RtcSession
        [Field/type]
            attr
        [Field/target]
            Integer
        [Field/isReadonly]
            true
        [Field/isRequired]
            true
`;
