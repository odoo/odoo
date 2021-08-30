/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            modelName
        [Field/model]
            Thread
        [Field/type]
            attr
        [Field/target]
            String
`;
