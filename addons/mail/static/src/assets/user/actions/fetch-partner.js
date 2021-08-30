/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Fetches the partner of this user.
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            User/fetchPartner
        [Action/params]
            user
                [Type]
                    User
        [Action/behavior]
            {User/performRpcRead}
                [context]
                    [active_test]
                        false
                [fields]
                    partner_id
                [ids]
                    @user
                    .{User/id}
`;
