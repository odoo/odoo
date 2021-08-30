/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            RtcConfigurationMenu/_onKeydown
        [Action/params]
            ev
                [type]
                    web.KeyboardEvent
            record
                [type]
                    RtcConfigurationMenu
        [Action/behavior]
            {if}
                @record
                .{RtcConfigurationMenu/isRegisteringKey}
                .{isFalsy}
            .{then}
                {break}
            {web.Event/stopPropagation}
                @ev
            {web.Event/preventDefault}
                @ev
            {UserSetting/setPushToTalkKey}
                [0]
                    @record
                    .{RtcConfigurationMenu/userSetting}
                [1]
                    @ev
`;
