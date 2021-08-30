/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            chainingType
        [Field/model]
            Activity
        [Field/type]
            attr
        [Field/target]
            String
        [Field/default]
            suggest
`;
