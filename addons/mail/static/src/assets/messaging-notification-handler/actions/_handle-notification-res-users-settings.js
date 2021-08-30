/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            MessagingNotificationHandler/_handleNotificationResUsersSettings
        [Action/params]
            settings
                [type]
                    Object
                [description]
                    @param {boolean} settings.use_push_to_talk
                    @param {String} settings.push_to_talk_key
                    @param {number} settings.voice_active_duration
                    @param {boolean} [settings.is_discuss_sidebar_category_channel_open]
                    @param {boolean} [settings.is_discuss_sidebar_category_chat_open]
                    @param {Object} [payload.volume_settings]
        [Action/behavior]
            {if}
                @settings
                .{Dict/hasKey}
                    is_discuss_sidebar_category_channel_open
            .{then}
                {Record/update}
                    [0]
                        {Discuss/categoryChannel}
                    [1]
                        [DiscussSidebarCategory/isServerOpen]
                            @settings
                            .{Dict/get}
                                is_discuss_sidebar_category_channel_open
            {if}
                @settings
                .{Dict/get}
                    is_discuss_sidebar_category_chat_open
            .{then}
                {Record/update}
                    [0]
                        {Discuss/categoryChat}
                    [1]
                        [DiscussSidebarCategory/isServerOpen]
                            @settings
                            .{Dict/get}
                                is_discuss_sidebar_category_chat_open
            {Record/update}
                [0]
                    {Env/userSetting}
                [1]
                    [UserSetting/usePushToTalk]
                        @settings
                        .{Dict/get}
                            use_push_to_talk
                    [UserSetting/pushToTalkKey]
                        @settings
                        .{Dict/get}
                            push_to_talk_key
                    [UserSetting/voiceActiveDuration]
                        @settings
                        .{Dict/get}
                            voice_active_duration
`;
