/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Checks whether this partner has a related employee and links them if
        applicable.
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            Partner/checkIsEmployee
        [Action/feature]
            hr
        [Action/params]
            partner
        [Action/behavior]
            {Record/doAsync}
                []
                    @partner
                []
                    {Employee/performRpcSearchRead}
                        [context]
                            [active_test]
                                false
                        [domain]
                            user_partner_id
                            .{=}
                                @partner
                                .{Partner/id}
                        [fields]
                            user_id
                            user_partner_id
            {Record/update}
                [0]
                    @partner
                [1]
                    [Partner/hasCheckedEmployee]
                        true
`;
