/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Test
        [Test/name]
            basic rendering
        [Test/model]
            MessagingMenuComponent
        [Test/assertions]
            20
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
                [Record/models]
                    MessagingMenuComponent
            {Test/assert}
                []
                    @testEnv
                    .{MessagingMenu/messagingMenuComponents}
                    .{Collection/length}
                    .{=}
                        1
                []
                    should have messaging menu
            {Test/assert}
                []
                    @testEnv
                    .{MessagingMenu/isOpen}
                    .{isFalsy}
                []
                    should not mark messaging menu item as shown by default
            {Test/assert}
                []
                    @testEnv
                    .{MessagingMenu/messagingMenuComponents}
                    .{Collection/first}
                    .{MessagingMenuComponent/toggler}
                []
                    should have clickable element on messaging menu
            {Test/assert}
                []
                    @testEnv
                    .{MessagingMenu/messagingMenuComponents}
                    .{Collection/first}
                    .{MessagingMenuComponent/icon}
                []
                    should have icon on clickable element in messaging menu
            {Test/assert}
                []
                    @testEnv
                    .{MessagingMenu/messagingMenuComponents}
                    .{Collection/first}
                    .{MessagingMenuComponent/icon}
                    .{web.Element/class}
                    .{String/includes}
                        fa-comments
                []
                    should have 'comments' icon on clickable element in messaging menu
            {Test/assert}
                []
                    @testEnv
                    .{MessagingMenu/messagingMenuComponents}
                    .{Collection/first}
                    .{MessagingMenuComponent/dropdownMenu}
                    .{isFalsy}
                []
                    should not display any messaging menu dropdown by default

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
                    .{MessagingMenu/isOpen}
                []
                    should mark messaging menu as opened
            {Test/assert}
                []
                    @testEnv
                    .{MessagingMenu/messagingMenuComponents}
                    .{Collection/first}
                    .{MessagingMenuComponent/dropdownMenu}
                []
                    should display messaging menu dropdown after click
            {Test/assert}
                []
                    @testEnv
                    .{MessagingMenu/messagingMenuComponents}
                    .{Collection/first}
                    .{MessagingMenuComponent/dropdownMenuHeader}
                []
                    should have dropdown menu header
            {Test/assert}
                []
                    @testEnv
                    .{MessagingMenu/messagingMenuComponents}
                    .{Collection/first}
                    .{MessagingMenuComponent/tabButton}
                    .{Collection/length}
                    .{=}
                        3
                []
                    should have 3 tab buttons to filter items in the header
            {Test/assert}
                []
                    @testEnv
                    .{MessagingMenu/messagingMenuComponents}
                    .{Collection/first}
                    .{MessagingMenuComponent/tabButton}
                    .{Collection/find}
                        {Record/insert}
                            [Record/models]
                                Function
                            [Function/in]
                                tabButton
                            [Function/out]
                                @tabButton
                                .{TabButton/id}
                                .{=}
                                    all
                []
                    1 tab button should be 'All'
            {Test/assert}
                []
                    @testEnv
                    .{MessagingMenu/messagingMenuComponents}
                    .{Collection/first}
                    .{MessagingMenuComponent/tabButton}
                    .{Collection/find}
                        {Record/insert}
                            [Record/models]
                                Function
                            [Function/in]
                                tabButton
                            [Function/out]
                                @tabButton
                                .{TabButton/id}
                                .{=}
                                    chat
                []
                    1 tab button should be 'Chat'
            {Test/assert}
                []
                    @testEnv
                    .{MessagingMenu/messagingMenuComponents}
                    .{Collection/first}
                    .{MessagingMenuComponent/tabButton}
                    .{Collection/find}
                        {Record/insert}
                            [Record/models]
                                Function
                            [Function/in]
                                tabButton
                            [Function/out]
                                @tabButton
                                .{TabButton/id}
                                .{=}
                                    channel
                []
                    1 tab button should be 'Channels'
            {Test/assert}
                []
                    @testEnv
                    .{MessagingMenu/messagingMenuComponents}
                    .{Collection/first}
                    .{MessagingMenuComponent/tabButton}
                    .{Collection/find}
                        {Record/insert}
                            [Record/models]
                                Function
                            [Function/in]
                                tabButton
                            [Function/out]
                                @tabButton
                                .{TabButton/id}
                                .{=}
                                    all
                    .{TabButton/isActive}
                []
                    'all' tab button should be active
            {Test/doesNotHaveClass}
                []
                    @testEnv
                    .{MessagingMenu/messagingMenuComponents}
                    .{Collection/first}
                    .{MessagingMenuComponent/tabButton}
                    .{Collection/find}
                        {Record/insert}
                            [Record/models]
                                Function
                            [Function/in]
                                tabButton
                            [Function/out]
                                @tabButton
                                .{TabButton/id}
                                .{=}
                                    chat
                    .{TabButton/isActive}
                    .{isFalsy}
                []
                    'chat' tab button should not be active
            {Test/doesNotHaveClass}
                []
                    @testEnv
                    .{MessagingMenu/messagingMenuComponents}
                    .{Collection/first}
                    .{MessagingMenuComponent/tabButton}
                    .{Collection/find}
                        {Record/insert}
                            [Record/models]
                                Function
                            [Function/in]
                                tabButton
                            [Function/out]
                                @tabButton
                                .{TabButton/id}
                                .{=}
                                    channel
                    .{TabButton/isActive}
                    .{isFalsy}
                []
                    'channel' tab button should not be active
            {Test/assert}
                []
                    @testEnv
                    .{MessagingMenu/messagingMenuComponents}
                    .{Collection/first}
                    .{MessagingMenuComponent/newMessageButton}
                []
                    should have button to make a new message
            {Test/assert}
                []
                    @testEnv
                    .{MessagingMenu/messagingMenuComponents}
                    .{Collection/first}
                    .{MessagingMenuComponent/notificationList}
                []
                    should display thread preview list
            {Test/assert}
                []
                    @testEnv
                    .{MessagingMenu/messagingMenuComponents}
                    .{Collection/first}
                    .{MessagingMenuComponent/notificationList}
                    .{NotificationListComponent/noConversation}
                []
                    should display no conversation in thread preview list

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
                    .{MessagingMenu/isOpen}
                    .{isFalsy}
                []
                    should mark messaging menu as closed
`;
