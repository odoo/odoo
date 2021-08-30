/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            Env/stop
        [Action/behavior]
            @env
            .{Env/owlEnv}
            .{Dict/get}
                services
            .{Dict/get}
                bus_service
            .{Dict/get}
                off
            .{Function/call}
                [0]
                    window_focus
                [1]
                    null
                [2]
                    {Env/_handleGlobalWindowFocus}
            {MessagingInitializer/stop}
            {MessagingNotificationHandler/stop}
`;
