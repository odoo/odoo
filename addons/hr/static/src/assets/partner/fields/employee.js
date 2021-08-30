/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Employee related to this partner. It is computed through
        the inverse relation and should be considered read-only.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            employee
        [Field/model]
            Partner
        [Field/feature]
            hr
        [Field/type]
            one
        [Field/target]
            Employee
        [Field/inverse]
            Employee/partner
`;
