/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            UserSetting/setDelayValue
        [Action/params]
            value
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
                    [UserSetting/voiceActiveDuration]
                        @value
            {if}
                {Env/isCurrentUserGuest}
                .{isFalsy}
            .{then}
                {UserSetting/_saveSettings}
                    @record
`;
