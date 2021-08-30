/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            RtcConfigurationMenuComponent/_onChangePushToTalk
        [Action/params]
            ev
                [type]
                    Event
            record
                [type]
                    RtcConfigurationMenuComponent
        [Action/behavior]
            {RtcConfigurationMenu/onChangePushToTalk}
                {Env/userSetting}
                .{UserSetting/rtcConfigurationMenu}
`;
