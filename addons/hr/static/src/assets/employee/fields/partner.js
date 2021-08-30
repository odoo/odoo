/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Partner related to this employee.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            partner
        [Field/model]
            Employee
        [Field/type]
            one
        [Field/target]
            Partner
        [Field/inverse]
            Partner/employee
        [Field/related]
            Employee/user
            user/partner
`;
