/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            MessagingInitializer/_initResUsersSettings
        [Action/params]
            id
                [type]
                    Integer
            is_discuss_sidebar_category_channel_open
                [type]
                    Boolean
            is_discuss_sidebar_category_chat_open
                [type]
                    Boolean
            messagingInitializer
                [type]
                    MessagingInitializer
        [Action/behavior]
            {Record/update}
                [0]
                    {Env/currentUser}
                [1]
                    [User/resUsersSettingsId]
                        @id
            {Record/update}
                [0]
                    @env
                [1]
                    [Env/userSetting]
                        {Record/insert}
                            [Record/models]
                                UserSetting
                            [UserSetting/id]
                                @id
                            [UserSetting/usePushToTalk]
                                @use_push_to_talk
                            [UserSetting/pushToTalkKey]
                                @push_to_talk_key
                            [UserSetting/voiceActiveDuration]
                                @voice_active_duration
                            [UserSetting/volumeSettings]
                                @volume_settings
            {Record/update}
                [0]
                    {Env/discuss}
                [1]
                    [Discuss/categoryChannel]
                        {Record/insert}
                            [Record/models]
                                DiscussSidebarCategory
                            [DiscussSidebarCategory/autocompleteMethod]
                                channel
                            [DiscussSidebarCategory/commandAddTitleText]
                                {Locale/text}
                                    Add or join a channel
                            [DiscussSidebarCategory/hasAddCommand]
                                true
                            [DiscussSidebarCategory/hasViewCommand]
                                true
                            [DiscussSidebarCategory/isServerOpen]
                                @is_discuss_sidebar_category_channel_open
                            [DiscussSidebarCategory/name]
                                {Locale/text}
                                    Channels
                            [DiscussSidebarCategory/newItemPlaceholderText]
                                {Locale/text}
                                    Find or create a channel...
                            [DiscussSidebarCategory/serverStateKey]
                                is_discuss_sidebar_category_channel_open
                            [DiscussSidebarCategory/sortComputeMethod]
                                name
                            [DiscussSidebarCategory/supportedChannelTypes]
                                channel
                    [Discuss/categoryChat]
                        {Record/insert}
                            [Record/models]
                                DiscussSidebarCategory
                            [DiscussSidebarCategory/autocompleteMethod]
                                chat
                            [DiscussSidebarCategory/commandAddTitleText]
                                {Locale/text}
                                    Start a conversation
                            [DiscussSidebarCategory/hasAddCommand]
                                true
                            [DiscussSidebarCategory/isServerOpen]
                                @is_discuss_sidebar_category_chat_open
                            [DiscussSidebarCategory/name]
                                {Locale/text}
                                    Direct Messages
                            [DiscussSidebarCategory/newItemPlaceholderText]
                                {Locale/text}
                                    Find or start a conversation...
                            [DiscussSidebarCategory/serverStateKey]
                                is_discuss_sidebar_category_chat_open
                            [DiscussSidebarCategory/sortComputeMethod]
                                last_action
                            [DiscussSidebarCategory/supportedChannelTypes]
                                chat
                                group
`;
