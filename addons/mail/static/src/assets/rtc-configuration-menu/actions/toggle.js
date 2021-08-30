/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            RtcConfigurationMenu/toggle
        [Action/params]
            record
                [type]
                    RtcConfigurationMenu
        [Action/behavior]
            {Record/update}
                [0]
                    @record
                [1]
                    [RtcConfigurationMenu/isOpen]
                        @record
                        .{RtcConfigurationMenu/isOpen}
                        .{isFalsy}
`;
