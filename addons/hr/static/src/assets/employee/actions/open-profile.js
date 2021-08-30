/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Opens the most appropriate view that is a profile for this employee.
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            Employee/openProfile
        [Action/params]
            employee
        [Action/behavior]
            {Env/openDocument}
                [id]
                    @employee
                    .{Employee/id}
                [model]
                    hr.employee.public
`;
