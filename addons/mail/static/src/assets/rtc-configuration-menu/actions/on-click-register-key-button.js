/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            RtcConfigurationMenu/onClickRegisterKeyButton
        [Action/params]
            ev
                [type]
                    MouseEvent
            record
                [type]
                    RtcConfigurationMenu
        [Action/behavior]
            {Record/update}
                [0]
                    @record
                [1]
                    [RtcConfigurationMenu/isRegisteringKey]
                        @record
                        .{RtcConfigurationMenu/isRegisteringKey}
                        .{isFalsy}
`;
