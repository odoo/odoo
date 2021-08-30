/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Renames this thread to the given new name.
        Only makes sense for channels.
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            Thread/rename
        [Action/params]
            newName
                [type]
                    String
            thread
                [type]
                    Thread
        [Action/behavior]
            {Record/update}
                [0]
                    @thread
                [1]
                    [Thread/name]
                        @newName
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
                    channel_rename
                [args]
                    {Record/insert}
                        [Record/models]
                            Collection
                        {Record/insert}
                            [Record/models]
                                Collection
                            @thread
                            .{Thread/id}
                [kwargs]
                    [name]
                        @newName
`;
