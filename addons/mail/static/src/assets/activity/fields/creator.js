/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            creator
        [Field/model]
            Activity
        [Field/type]
            one
        [Field/target]
            User
`;
