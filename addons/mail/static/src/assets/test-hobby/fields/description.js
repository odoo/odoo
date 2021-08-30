/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            description
        [Field/model]
            TestHobby
        [Field/type]
            attr
        [Field/target]
            String
        [Field/isReadonly]
            true
        [Field/isRequired]
            true
`;
