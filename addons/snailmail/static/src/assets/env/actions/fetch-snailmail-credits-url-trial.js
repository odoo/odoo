/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            Env/fetchSnailmailCreditsUrlTrial
        [Action/feature]
            snailmail
        [Action/behavior]
            :snailmailCreditsUrlTrial
                {Record/doAsync}
                    [0]
                        @env
                    [1]
                        @env
                        .{Env/owlEnv}
                        .{Dict/get}
                            services
                        .{Dict/get}
                            rpc
                        .{Function/call}
                            [model]
                                iap.account
                            [method]
                                get_credits_url
                            [args]
                                {Record/insert}
                                    [Record/models]
                                        Collection
                                    [0]
                                        snailmail
                                    [1]
                                        {String/empty}
                                    [2]
                                        0
                                    [3]
                                        true
            {Record/update}
                [0]
                    @env
                [1]
                    [Env/snailmailCreditsUrlTrial]
                        @snailmailCreditsUrlTrial
`;
