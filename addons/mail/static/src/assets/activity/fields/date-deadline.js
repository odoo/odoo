/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            dateDeadline
        [Field/model]
            Activity
        [Field/type]
            attr
        [Field/target]
            Date
`;
