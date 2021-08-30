/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Test
        [Test/name]
            composer state conservation on toggle discuss
        [Test/model]
            ChatWindowManagerComponent
        [Test/assertions]
            6
        [Test/scenario]
            {Dev/comment}
                channel that is expected to be found in the messaging menu
                with random unique id that is needed to link messages
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
            @testEnv
            .{Record/insert}
                [Record/models]
                    ChatWindowManagerComponent
            :messagingMenuComponent
                @testEnv
                .{Record/insert}
                    [Record/models]
                        MessagingMenuComponent
            @testEnv
            .{Component/afterNextRender}
                @testEnv
                .{UI/click}
                    @testEnv
                    .{MessagingMenu/messagingMenuComponents}
                    .{Collection/first}
                    .{MessagingMenuComponent/toggler}
            @testEnv
            .{Component/afterNextRender}
                @testEnv
                .{UI/click}
                    @testEnv
                    .{MessagingMenu/messagingMenuComponents}
                    .{Collection/first}
                    .{MessagingMenuComponent/notificationList}
                    .{NotificationListComponent/threadPreview}
                    .{Collection/first}
            {Dev/comment}
                Set content of the composer of the chat window
            @testEnv
            .{Component/afterNextRender}
                @testEnv
                .{UI/focus}
                    @testEnv
                    .{Record/findById}
                        [Thread/id]
                            20
                        [Thread/model]
                            mail.channel
                    .{Thread/composer}
                    .{Composer/composerTextInputComponents}
                    .{Collection/first}
                    .{ComposerTextInputComponent/textarea}
                @testEnv
                .{insertText}
                    XDU for the win !
            {Test/assert}
                []
                    @testEnv
                    .{Record/findById}
                        [Thread/id]
                            20
                        [Thread/model]
                            mail.channel
                    .{Thread/composer}
                    .{Composer/attachments}
                    .{Collection/length}
                    .{=}
                        0
                []
                    composer should have no attachment initially
            {Dev/comment}
                Set attachments of the composer
            :files
                {Record/insert}
                    [Record/models]
                        Collection
                    [0]
                        {Record/insert}
                            [Record/models]
                                web.File
                            [web.File/name]
                                text state conservation on toggle discuss.txt
                            [web.File/content]
                                hello, world
                            [web.File/contentType]
                                text/plain
                    [1]
                        {Record/insert}
                            [Record/models]
                                web.File
                            [web.File/name]
                                text2 state conservation on toggle discuss.txt
                            [web.File/content]
                                hello, xdu is da best man
                            [web.File/contentType]
                                text/plain
            @testEnv
            .{Component/afterNextRender}
                @testEnv
                .{UI/inputFiles}
                    [0]
                        @testEnv
                        .{ChatWindowManager/chatWindows}
                        .{Collection/first}
                        .{ChatWindow/threadView}
                        .{ThreadView/composerView}
                        .{ComposerView/fileUploader}
                        .{FileUploader/fileInput}
                    [1]
                        @files
            {Test/assert}
                []
                    @testEnv
                    .{Record/findById}
                        [Thread/id]
                            20
                        [Thread/model]
                            mail.channel
                    .{Thread/composer}
                    .{Composer/composerTextInputComponents}
                    .{Collection/first}
                    .{ComposerTextInputComponent/textarea}
                    .{web.Element/value}
                    .{=}
                        XDU for the win !
                []
                    chat window composer initial text input should contain 'XDU for the win !'
            {Test/assert}
                []
                    @testEnv
                    .{Record/findById}
                        [Thread/id]
                            20
                        [Thread/model]
                            mail.channel
                    .{Thread/composer}
                    .{Composer/attachments}
                    .{Collection/length}
                    .{=}
                        2
                []
                    composer should have 2 total attachments after adding 2 attachments

            @testEnv
            .{UI/afterNextRender}
                @testEnv
                .{Discuss/open}
            {Test/assert}
                []
                    @testEnv
                    .{ChatWindowManager/chatWindowManagerComponents}
                    .{Collection/first}
                    .{ChatWindowManagerComponent/chatWindows}
                    .{Collection/length}
                    .{=}
                        0
                []
                    should not have any chat window after opening discuss

            @testEnv
            .{UI/afterNextRender}
                @testEnv
                .{Discuss/close}
            {Test/assert}
                []
                    @testEnv
                    .{Record/findById}
                        [Thread/id]
                            20
                        [Thread/model]
                            mail.channel
                    .{Thread/composer}
                    .{Composer/composerTextInputComponents}
                    .{Collection/first}
                    .{ComposerTextInputComponent/textarea}
                    .{web.Element/value}
                    .{=}
                        XDU for the win !
                []
                    chat window composer should still have the same input after closing discuss
            {Test/assert}
                []
                    @testEnv
                    .{Record/findById}
                        [Thread/id]
                            20
                        [Thread/model]
                            mail.channel
                    .{Thread/composer}
                    .{Composer/attachments}
                    .{Collection/length}
                    .{=}
                        2
                []
                    chat window composer should have 2 attachments closing discuss
`;
