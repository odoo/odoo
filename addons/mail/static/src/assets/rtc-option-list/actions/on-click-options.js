/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            RtcOptionList/onClickOptions
        [Action/params]
            ev
                [type]
                    MouseEvent
            record
                [type]
                    RtcOptionList
        [Action/behavior]
            {RtcConfigurationMenu/toggle}
                {Env/userSetting}
                .{UserSetting/rtcConfigurationMenu}
            {Component/trigger}
                [0]
                    @record
                    .{RtcOptionList/component}
                [1]
                    o-popover-close
`;
