/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            RtcConfigurationMenuComponent/_onChangeThreshold
        [Action/params]
            ev
                [type]
                    web.Event
            record
                [type]
                    RtcConfigurationMenuComponent
        [Action/behavior]
            {RtcConfigurationMenu/onChangeThreshold}
                [0]
                    {Env/userSetting}
                    .{UserSetting/rtcConfigurationMenu}
                [1]
                    @ev
                    .{web.Event/target}
                    .{web.Element/value}
`;
