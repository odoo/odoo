/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Starts env and related records.
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            Env/start
        [Action/behavior]
            @env
            .{Env/owlEnv}
            .{Dict/get}
                services
            .{Dict/get}
                bus_service
            .{Dict/get}
                on
            .{Function/call}
                [0]
                    window_focus
                [1]
                    null
                [2]
                    {Env/_handleGlobalWindowFocus}
            {Record/doAsync}
                [0]
                    @env
                [1]
                    {MessagingInitializer/start}
            {MessagingNotificationHandler/start}
            {Record/update}
                [0]
                    @env
                [1]
                    [Env/isInitialized]
                        true
                    [Env/initializedPromise]
                            {Promise/resolve}
`;
