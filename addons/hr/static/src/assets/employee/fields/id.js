/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Unique identifier for this employee.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            id
        [Field/model]
            Employee
        [Field/type]
            attr
        [Field/target]
            Number
        [Field/isReadonly]
            true
`;
