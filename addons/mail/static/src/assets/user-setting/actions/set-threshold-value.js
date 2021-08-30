/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            UserSetting/setThresholdValue
        [Action/params]
            voiceActivationThreshold
                [type]
                    Float
            record
                [type]
                    UserSetting
        [Action/behavior]
            {Record/update}
                [0]
                    @record
                [1]
                    [UserSetting/voiceActivationThreshold]
                        @voiceActivationThreshold
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
                    mail_user_setting_voice_threshold
                [1]
                    @voiceActivationThreshold
            {Rtc/updateVoiceActivation}
`;
