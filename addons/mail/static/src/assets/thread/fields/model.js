/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            model
        [Field/model]
            Thread
        [Field/type]
            attr
        [Field/target]
            String
        [Field/isRequired]
            true
        [Field/isReadonly]
            true
`;
