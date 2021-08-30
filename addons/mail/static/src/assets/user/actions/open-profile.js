/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Opens the most appropriate view that is a profile for this user.
        Because user is a rather technical model to allow login, it's the
        partner profile that contains the most useful information.
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            User/openProfile
        [Action/params]
            user
                [type]
                    User
        [Action/behavior]
            {if}
                @user
                .{User/partner}
                .{isFalsy}
            .{then}
                {Record/doAsync}
                    [0]
                        @user
                    [1]
                        {User/fetchPartner}
                            @user
            {if}
                @user
                .{User/partner}
                .{isFalsy}
            .{then}
                {Dev/comment}
                    This user has been deleted from the server or never existed:
                    - Validity of id is not verified at insert.
                    - There is no bus notification in case of user delete from
                      another tab or by another user.
                @env
                .{Env/owlEnv}
                .{Dict/get}
                    services
                .{Dict/get}
                    notification
                .{Dict/get}
                    notify
                .{Function/call}
                    [message]
                        {Locale/text}
                            You can only open the profile of existing users.
                    [type]
                        warning
                {break}
            {Partner/openProfile}
                @user
                .{User/partner}
`;
