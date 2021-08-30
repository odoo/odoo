/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Test
        [Test/name]
            post a simple message
        [Test/model]
            DiscussComponent
        [Test/assertions]
            16
        [Test/scenario]
            {Dev/comment}
                channel expected to be found in the sidebar
                with a random unique id that will be referenced in the test
            :testEnv
                {Record/insert}
                    [Record/models]
                        Env
            @testEnv
            .{Record/insert}
                [Record/models]
                    mail.channel
                [mail.channel/id]
                    20
            @testEnv
            .{Record/insert}
                [Record/models]
                    Server
                [Server/data]
                    @record
                    .{Test/data}
                [Server/mockRPC]
                    {Record/insert}
                        [Record/models]
                            Function
                        [Function/in]
                            route
                            args
                            original
                        [Function/out]
                            :res
                                @original
                            {if}
                                @route
                                .{=}
                                    /mail/message/post
                            .{then}
                                {Test/step}
                                    message_post
                                {Test/assert}
                                    []
                                        @args
                                        .{Dict/get}
                                            thread_model
                                        .{=}
                                            mail.channel
                                    []
                                        should post message to channel
                                {Test/assert}
                                    []
                                        @args
                                        .{Dict/get}
                                            thread_id
                                        .{=}
                                            20
                                    []
                                        should post message to channel Id 20
                                {Test/assert}
                                    []
                                        @args
                                        .{Dict/get}
                                            post_data
                                        .{Dict/get}
                                            body
                                        .{=}
                                            Test
                                    []
                                        should post with provided content in composer input
                                {Test/assert}
                                    []
                                        @args
                                        .{Dict/get}
                                            post_data
                                        .{Dict/get}
                                            message_type
                                        .{=}
                                            comment
                                    []
                                        should set message type as 'comment'
                                {Test/assert}
                                    []
                                        @args
                                        .{Dict/get}
                                            post_data
                                        .{Dict/get}
                                            subtype_xmlid
                                        .{=}
                                            mail.mt_comment
                                    []
                                        should set subtype_xmlid as 'comment'
                                :postedMessageId
                                    @res
                                    .{Dict/get}
                                        id
                            @res
            @testEnv
            .{Record/insert}
                [Record/models]
                    DiscussComponent
            @testEnv
            .{Thread/open}
                @testEnv
                .{Record/findById}
                    [Thread/id]
                        20
                    [Thread/model]
                        mail.channel
            {Test/assert}
                []
                    @testEnv
                    .{Discuss/thread}
                    .{Thread/threadViews}
                    .{Collection/first}
                    .{ThreadView/messageListComponents}
                    .{Collection/first}
                    .{MessageListComponent/empty}
                []
                    should display thread with no message initially
            {Test/assert}
                []
                    @testEnv
                    .{Discuss/thread}
                    .{Thread/cache}
                    .{ThreadCache/messages}
                    .{Collection/length}
                    .{=}
                        0
                []
                    should display no message initially
            {Test/assert}
                []
                    @testEnv
                    .{Discuss/thread}
                    .{Thread/composer}
                    .{Composer/composerTextInputComponents}
                    .{Collection/first}
                    .{ComposerTextInputComponent/textarea}
                    .{web.Element/value}
                    .{=}
                        {String/empty}
                []
                    should have empty content initially

            {Dev/comment}
                insert some HTML in editable
            @testEnv
            .{Component/afterNextRender}
                @testEnv
                .{UI/focus}
                    @testEnv
                    .{Discuss/thread}
                    .{Thread/composer}
                    .{Composer/composerTextInputComponents}
                    .{Collection/first}
                    .{ComposerTextInputComponent/textarea}
                @testEnv
                .{UI/insertText}
                    Test
            {Test/assert}
                []
                    @testEnv
                    .{Discuss/thread}
                    .{Thread/composer}
                    .{Composer/composerTextInputComponents}
                    .{Collection/first}
                    .{ComposerTextInputComponent/textarea}
                    .{web.Element/value}
                    .{=}
                        Test
                []
                    should have inserted text in editable

            @testEnv
            .{Component/afterNextRender}
                @testEnv
                .{UI/click}
                    @testEnv
                    .{Discuss/thread}
                    .{Thread/composer}
                    .{Composer/composerViewComponents}
                    .{Colection/first}
                    .{ComposerViewComponent/buttonSend}
            {Test/verifySteps}
                message_post
            {Test/assert}
                []
                    @testEnv
                    .{Discuss/thread}
                    .{Thread/composer}
                    .{Composer/composerTextInputComponents}
                    .{Collection/first}
                    .{ComposerTextInputComponent/textarea}
                    .{web.Element/value}
                    .{=}
                        {String/empty}
                []
                    should have no content in composer input after posting message
            {Test/assert}
                []
                    @testEnv
                    .{Discuss/thread}
                    .{Thread/cache}
                    .{ThreadCache/messages}
                    .{Collection/length}
                    .{=}
                        1
                []
                    should display a message after posting message
            {Test/assert}
                []
                    @testEnv
                    .{Discuss/thread}
                    .{Thread/cache}
                    .{ThreadCache/messages}
                    .{Collection/first}
                    .{=}
                        @testEnv
                        .{Record/findById}
                            [Message/id]
                                @postedMessageId
                []
                    new message in thread should be linked to newly created message from message post
            {Test/assert}
                []
                    @testEnv
                    .{Discuss/thread}
                    .{Thread/cache}
                    .{ThreadCache/messages}
                    .{Collection/first}
                    .{Message/messageComponents}
                    .{Collection/first}
                    .{messageComponent/authorName}
                    .{web.Element/textContent}
                    .{=}
                        Mitchell Admin
                []
                    new message in thread should be from current partner name
            {Test/assert}
                []
                    @testEnv
                    .{Discuss/thread}
                    .{Thread/cache}
                    .{ThreadCache/messages}
                    .{Collection/first}
                    .{Message/messageComponents}
                    .{Collection/first}
                    .{MessageViewComponent/content}
                    .{web.Element/textContent}
                    .{=}
                        Test
                []
                    new message in thread should have content typed from composer text input
`;
