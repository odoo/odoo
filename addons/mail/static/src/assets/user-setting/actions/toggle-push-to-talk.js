/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            UserSetting/togglePushToTalk
        [Action/params]
            record
                [type]
                    UserSetting
        [Action/behavior]
            {Record/update}
                [0]
                    @record
                [1]
                    [UserSetting/usePushToTalk]
                        @record
                        .{UserSetting/usePushToTalk}
                        .{isFalsy}
            {Rtc/updateVoiceActivation}
            {if}
                {Env/isCurrentUserGuest}
                .{isFalsy}
            .{then}
                {UserSetting/_saveSettings}
                    @record
`;
