/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Checks whether this employee has a related user and partner and links
        them if applicable.
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            Employee/checkIsUser
        [Action/params]
            employee
        [Action/behavior]
            {Employee/performRpcRead}
                [context]
                    [active_test]
                        false
                [fields]
                    user_id
                    user_partner_id
                [ids]
                    @employee
                    .{Employee/id}
`;
