/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            RtcConfigurationMenuComponent/_onClickRegisterKeyButton
        [Action/params]
            ev
                [type]
                    MouseEvent
            record
                [type]
                    RtcConfigurationMenuComponent
        [Action/behavior]
            {RtcConfigurationMenu/onClickRegisterKeyButton}
                {Env/userSetting}
                .{UserSetting/rtcConfigurationMenu}
`;
