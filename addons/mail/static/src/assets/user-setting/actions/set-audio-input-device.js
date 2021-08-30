/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            UserSetting/setAudioInputDevice
        [Action/params]
            audioInputDeviceId
                [type]
                    String
            record
                [type]
                    UserSetting
        [Action/behavior]
            {Record/update}
                [0]
                    @record
                [1]
                    [UserSetting/audioInputDeviceId]
                        @audioInputDeviceId
            @env
            .{Env/owlEnv}
            .{Dict/get}
                services
            .{Dict/get}
                local_storage
            .{Dict/get}
                setItem
            .{Function/call}
                [0]
                    mail_user_setting_audio_input_device_id
                [1]
                    @audioInputDeviceId
            {Rtc/updateLocalAudioTrack}
                true
`;
