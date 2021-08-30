/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Test
        [Test/name]
            basic rendering
        [Test/model]
            MessageViewComponent
        [Test/assertions]
            11
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
            :message
                @testEnv
                .{Record/insert}
                    [Record/models]
                        Message
                    [Message/author]
                        @testEnv
                        .{Record/insert}
                            [Record/models]
                                Partner
                            [Partner/displayName]
                                Demo User
                            [Partner/id]
                                7
                    [Message/body]
                        <p>Test</p>
                    [Message/date]
                        @testEnv
                        .{Record/insert}
                            [Record/models]
                                Moment
                    [Message/id]
                        100
            @testEnv
            .{Record/insert}
                [Record/models]
                    MessageViewComponent
                [MessageViewComponent/message]
                    @message
            {Test/assert}
                []
                    @message
                    .{Message/messageComponents}
                    .{Collection/length}
                    .{=}
                        1
                []
                    should display a message component
            {Test/assert}
                []
                    @message
                    .{Message/messageComponents}
                    .{Collection/first}
                    .{MessageViewComponent/sidebar}
                []
                    message should have a sidebar
            {Test/assert}
                []
                    @message
                    .{Message/messageComponents}
                    .{Collection/first}
                    .{MessageViewComponent/authorAvatar}
                []
                    message should have author avatar in the sidebar
            {Test/assert}
                []
                    @message
                    .{Message/messageComponents}
                    .{Collection/first}
                    .{MessageViewComponent/authorAvatar}
                    .{web.Element/tag}
                    .{=}
                        img
                []
                    message author avatar should be an image
            {Test/assert}
                []
                    @message
                    .{Message/messageComponents}
                    .{Collection/first}
                    .{MessageViewComponent/authorAvatar}
                    .{web.Element/src}
                    .{=}
                        /web/image/res.partner/7/avatar_128
                []
                    message author avatar should GET image of the related partner
            {Test/assert}
                []
                    @message
                    .{Message/messageComponents}
                    .{Collection/first}
                    .{MessageViewComponent/authorName}
                []
                    message should display author name
            {Test/assert}
                []
                    @message
                    .{Message/messageComponents}
                    .{Collection/first}
                    .{MessageViewComponent/authorName}
                    .{web.Element/textContent}
                    .{=}
                        Demo User
                []
                    message should display correct author name
            {Test/assert}
                []
                    @message
                    .{Message/messageComponents}
                    .{Collection/first}
                    .{MessageViewComponent/date}
                []
                    message should display date

            @testEnv
            .{UI/click}
                @message
                .{Message/messageComponents}
                .{Collection/first}
            {Test/assert}
                []
                    @message
                    .{Message/actionList}
                    .{MessageActionList/messageActionListComponents}
                    .{Collection/length}
                    .{=}
                        1
                []
                    message should display list of actions
            {Test/assert}
                []
                    @message
                    .{Message/messageComponents}
                    .{Collection/first}
                    .{MessageViewComponent/content}
                []
                    message should display the content
            {Test/assert}
                []
                    @message
                    .{Message/messageComponents}
                    .{Collection/first}
                    .{MessageViewComponent/prettyBody}
                    .{web.Element/htmlContent}
                    .{=}
                        <p>Test</p>
                []
                    message should display the correct content
`;
