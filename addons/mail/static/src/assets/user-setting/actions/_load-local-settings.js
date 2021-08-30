/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            UserSetting/_loadLocalSettings
        [Action/params]
            record
                [type]
                    UserSetting
        [Action/behavior]
            :voiceActivationThreshold
                @env
                .{Env/owlEnv}
                .{Dict/get}
                    services
                .{Dict/get}
                    local_storage
                .{Dict/get}
                    getItem
                .{Function/call}
                    mail_user_setting_voice_threshold
            :audioInputDeviceId
                @env
                .{Env/owlEnv}
                .{Dict/get}
                    services
                .{Dict/get}
                    local_storage
                .{Dict/get}
                    getItem
                .{Function/call}
                    mail_user_setting_audio_input_device_id
            {if}
                @voiceActivationThreshold
                .{>}
                    0
            .{then}
                {Record/update}
                    [0]
                        @record
                    [1]
                        [UserSetting/voiceActivationThreshold]
                            @voiceActivationThreshold
                        [UserSetting/audioInputDeviceId]
                            @audioInputDeviceId
`;
