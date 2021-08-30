/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            UserSetting/_saveSettings
        [Action/params]
            record
                [type]
                    UserSetting
        [Action/behavior]
            {Browser/clearTimeout}
                @recod
                .{UserSetting/globalSettingsTimeout}
            {Record/update}
                [0]
                    @record
                [1]
                    [UserSetting/globalSettingsTimeout]
                        {Browser/setTimeout}
                            [0]
                                {UserSetting/_onSaveGlobalSettingsTimeout}
                                    @record
                            [1]
                                2000
`;
