/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Changes description of the thread to the given new description.
        Only makes sense for channels.
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            Thread/changeDescription
        [Action/params]
            description
                [type]
                    String
            thread
                [type]
                    Thread
        [Action/behavior]
            {Record/update}
                [0]
                    @thread
                [out]
                    [Thread/description]
                        @description
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
                    channel_change_description
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
                    [description]
                        @description
`;
