/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Mark the specified conversation as fetched.
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            Thread/markAsFetched
        [Action/params]
            thread
                [type]
                    Thread
        [Action/behavior]
            {Record/doAsync}
                [0]
                    @thread
                [1]
                    @env
                    .{Env/owlEnv}
                    .{Dict/get}
                        services
                    .{Dict/get}
                        rpc
                    .{Function/call}
                        [0]
                            [model]
                                mail.channel
                            [method]
                                channel_fetched
                            [args]
                                {Record/insert}
                                    [Record/models]
                                        Collection
                                    {Record/insert}
                                        [Record/models]
                                            Collection
                                        @thread
                                        .{Thread/id}
                        [1]
                            [shadow]
                                true
`;
