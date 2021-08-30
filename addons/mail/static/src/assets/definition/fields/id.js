/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            id
        [Field/model]
            Definition
        [Field/type]
            attr
        [Field/target]
            String
        [Field/isRequired]
            true
`;
