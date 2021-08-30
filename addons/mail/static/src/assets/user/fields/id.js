/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            id
        [Field/model]
            User
        [Field/type]
            attr
        [Field/isReadonly]
            true
`;
