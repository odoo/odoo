/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            UserSetting/toggleLayoutSettingsWindow
        [Action/params]
            record
                [type]
                    UserSetting
        [Action/behavior]
            {Record/update}
                [0]
                    @record
                [1]
                    [UserSetting/isRtcLayoutSettingDialogOpen]
                        @record
                        .{UserSetting/isRtcLayoutSettingDialogOpen}
                        .{isFalsy}
`;
