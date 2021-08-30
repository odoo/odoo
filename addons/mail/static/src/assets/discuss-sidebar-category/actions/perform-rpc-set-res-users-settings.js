/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Performs the 'set_res_users_settings' RPC on 'res.users.settings'.
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            DiscussSidebarCategory/performRpcSetResUsersSettings
        [Action/params]
            resUsersSettings
                [type]
                    Object
                [description]
                    @param {boolean} [resUsersSettings.is_category_channel_open]
                    @param {boolean} [resUsersSettings.is_category_chat_open]
        [Action/behavior]
            @env
            .{Env/owlEnv}
            .{Dict/get}
                services
            .{Dict/get}
                rpc
            .{Function/call}
                [0]
                    [model]
                        res.users.settings
                    [method]
                        set_res_users_settings
                    [args]
                        {Record/insert}
                            [Record/models]
                                Collection
                            {Record/insert}
                                [Record/models]
                                    Collection
                                {Env/currentUser}
                                .{User/resUsersSettingsId}
                    [kwargs]
                        [new_settings]
                            @resUsersSettings
                [1]
                    [shadow]
                        true
`;
