/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        User related to this employee.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            user
        [Field/model]
            Employee
        [Field/type]
            one
        [Field/target]
            User
        [Field/inverse]
            User/employee
`;
