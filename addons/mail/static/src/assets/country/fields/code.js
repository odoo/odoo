/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            code
        [Field/model]
            Country
        [Field/type]
            attr
        [Field/target]
            String
`;
