/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            ActionAddon
        [ActionAddon/action]
            Env/openProfile
        [ActionAddon/feature]
            hr
        [ActionAddon/params]
            id
            model
        [ActionAddon/behavior]
            {if}
                @model
                .{=}
                    hr.employee
                .{|}
                    @model
                    .{=}
                        hr.employee.public
            .{then}
                :employee
                    {Record/models}
                        [Record/models]
                            Employee
                        [Employee/id]
                            @id
                {Employee/openProfile}
                    @employee
            .{else}
                    @original
`;
