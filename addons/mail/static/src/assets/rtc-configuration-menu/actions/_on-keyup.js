/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            RtcConfigurationMenu/_onKeyup
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
            {Record/update}
                [0]
                    @record
                [1]
                    [RtcConfigurationMenu/isRegisteringKey]
                        false
`;
