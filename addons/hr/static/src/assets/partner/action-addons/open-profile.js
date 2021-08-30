/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        When a partner is an employee, its employee profile contains more useful
        information to know who he is than its partner profile.
    {Record/insert}
        [Record/models]
            ActionAddon
        [ActionAddon/action]
            Partner/openProfile
        [ActionAddon/feature]
            hr
        [ActionAddon/params]
            options
            partner
        [ActionAddon/behavior]
            {if}
                @partner
                .{Partner/employee}
                .{isFalsy}
                .{&}
                    @partner
                    .{Partner/hasCheckedEmployee}
                    .{isFalsy}
            .{then}
                {Record/doAsync}
                    []
                        @partner
                    []
                        {Partner/checkIsEmployee}
                            @partner
            {if}
                @partner
                .{Partner/employee}
            .{then}
                {Employee/openProfile}
                    @partner
                    .{Partner/employee}
            @original
`;
