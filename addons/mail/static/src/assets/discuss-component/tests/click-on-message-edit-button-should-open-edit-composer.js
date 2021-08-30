/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Test
        [Test/name]
            click on message edit button should open edit composer
        [Test/model]
            DiscussComponent
        [Test/assertions]
            1
        [Test/scenario]
            :testEnv
                {Record/insert}
                    [Record/models]
                        Env
            @testEnv
            .{Record/insert}
                [Record/models]
                    Server
                [Server/data]
                    @record
                    .{Test/data}
            @testEnv
            .{Record/insert}
                []
                    [Record/models]
                        mail.channel
                    [mail.channel/id]
                        20
                []
                    [Record/models]
                        mail.message
                    [mail.message/body]
                        not empty
                    [mail.message/message_type]
                        comment
                    [mail.message/model]
                        mail.channel
                    [mail.message/res_id]
                        20
            @testEnv
            .{Record/insert}
                [Record/models]
                    DiscussComponent
            @testEnv
            .{Record/update}
                []
                    {Env/Discuss}
                []
                    [Discuss/activeId]
                        mail.channel_20
            @testEnv
            .{UI/click}
                @testEnv
                .{Record/all}
                    MessageViewComponent
                .{Collection/first}
            @testEnv
            .{UI/click}
                @testEnv
                .{Record/all}
                    MessageActionListComponent
                .{Collection/first}
                .{MessageActionListComponent/actionEdit}
            {Test/assert}
                []
                    @testEnv
                    .{Record/all}
                        MessageComponent
                    .{Collection/first}
                    .{MessageComponent/composer}
                []
                    click on message edit button should open edit composer
`;
