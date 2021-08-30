/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Sets the custom name of this thread for the current user to the given
        new name.
        Only makes sense for channels.
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            Thread/setCustomName
        [Action/params]
            thread
                [type]
                    Thread
            newName
                [type]
                    String
        [Action/behavior]
            @env
            .{Env/owlEnv}
            .{Dict/get}
                services
            .{Dict/get}
                rpc
            .{Function/call}
                [model]
                    mail.channel
                [method]
                    channel_set_custom_name
                [args]
                    {Record/insert}
                        [Record/models]
                            Collection
                        @thread
                        .{Thread/id}
                [kwargs]
                    [name]
                        @newName
`;
