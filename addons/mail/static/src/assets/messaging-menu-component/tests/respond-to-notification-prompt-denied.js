/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Test
        [Test/name]
            respond to notification prompt (denied)
        [Test/model]
            MessagingMenuComponent
        [Test/assertions]
            4
        [Test/scenario]
            :testEnv
                {Record/insert}
                    [Record/models]
                        Env
                    [Env/owlEnv]
                        [browser]
                            [Notification]
                                [permission]
                                    default
                                [requestPermission]
                                    {Record/insert}
                                        [Record/models]
                                            Function
                                        [Function/in]
                                            self
                                        [Function/out]
                                            {Record/update}
                                                [0]
                                                    @self
                                                [1]
                                                    [permission]
                                                        denied
                                            @self
                                            .{Dict/get}
                                                permission
                        [services]
                            [notification]
                                [notify]
                                    {Test/step}
                                        should display a toast notification with the deny confirmation
            @testEnv
            .{Record/insert}
                [Record/models]
                    MessagingMenuComponent
            @testEnv
            .{Record/insert}
                [Record/models]
                    Server
                [Server/data]
                    @record
                    .{Test/data}
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
                    .{NotificationListComponent/notificationRequest}
            {Test/verifySteps}
                should display a toast notification with the deny confirmation
            {Test/assert}
                []
                    @testEnv
                    .{MessagingMenu/messagingMenuComponents}
                    .{Collection/first}
                    .{MessagingMenuComponent/counter}
                    .{isFalsy}
                []
                    should not display a notification counter next to the messaging menu

            @testEnv
            .{Component/afterNextRender}
                @testEnv
                .{UI/click}
                    @testEnv
                    .{MessagingMenu/messagingMenuComponents}
                    .{Collection/first}
                    .{MessagingMenuComponent/toggler}
            {Test/assert}
                []
                    @testEnv
                    .{MessagingMenu/messagingMenuComponents}
                    .{Collection/first}
                    .{MessagingMenuComponent/notificationList}
                    .{NotificationListComponent/notificationRequest}
                    .{isFalsy}
                []
                    should display no notification in the messaging menu
`;
