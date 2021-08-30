/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            Thread/createGroupChat
        [Action/params]
            default_display_mode
                [type]
                    String
                    .{|}
                        Boolean
            partner_to
                [type]
                    Collection<Number>
        [Action/returns]
            Thread
        [Action/behavior]
            :channelData
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
                        create_group
                    [kwargs]
                        [default_display_mode]
                            @default_display_mode
                        [partners_to]
                            @partners_to
            {Record/insert}
                [Record/models]
                    Thread
                {Thread/convertData}
                    @channelData
`;
