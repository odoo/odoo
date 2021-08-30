/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            ActionAddon
        [ActionAddon/actionName]
            Env/getChat
        [ActionAddon/feature]
            hr
        [ActionAddon/params]
            employeeId
        [ActionAddon/behavior]
            {if}
                @employeeId
            .{then}
                :employee
                    {Record/insert}
                        [Record/models]
                            Employee
                        [Employee/id]
                            employeeId
                {Employee/getChat}
                    @employee
            .{else}
                @original
`;
