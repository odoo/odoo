/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            Guest/performRpcGuestUpdateName
        [Action/params]
            id
                [type]
                    Number
                [description]
                    The id of the guest to rename.
            name
                [type]
                    String
                [description]
                    The new name to use to rename the guest.
        [Action/behavior]
            @env
            .{Env/owlEnv}
            .{Dict/get}
                services
            .{Dict/get}
                rpc
            .{Function/call}
                [route]
                    /mail/guest/update_name
                [params]
                    [guest_id]
                        @id
                    [name]
                        @name
`;
