/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            Device/_refresh
        [Action/params]
            device
        [Action/behavior]
            {Record/update}
                [0]
                    @device
                [1]
                    {Dev/comment}
                        AKU TODO: turn all fields as computed fields
                    [Device/globalWindowInnerHeight]
                        {web.Browser/innerHeight}
                    [Device/globalWindowInnerWidth]
                        {web.Browser/innerWidth}
                    [Device/isMobile]
                        @env
                        .{Env/owlEnv}
                        .{Dict/get}
                            device
                        .{Dict/get}
                            isMobile
                    [Device/isMobileDevice]
                        {Device/isMobileDevice}
                    [Device/sizeClass]
                        @env
                        .{Env/owlEnv}
                        .{Dict/get}
                            device
                        .{Dict/get}
                            size_class
`;
