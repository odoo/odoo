/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            id
        [Field/model]
            Partner
        [Field/type]
            attr
        [Field/target]
            Number
        [Field/isReadonly]
            true
        [Field/isRequired]
            true
`;
