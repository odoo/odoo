/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Unstar all starred messages of current user.
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            Message/unstarAll
        [Action/behavior]
            @env
            .{Env/owlEnv}
            .{Dict/get}
                services
            .{Dict/get}
                rpc
            .{Function/call}
                [model]
                    mail.message
                [method]
                    unstar_all
`;
