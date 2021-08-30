/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            difficulty
        [Field/model]
            TestTask
        [Field/type]
            attr
        [Field/target]
            Number
        [Field/default]
            1
`;
