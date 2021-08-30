/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Lifecycle
        [Lifecycle/name]
            onDelete
        [Lifecycle/model]
            UserSetting
        [Lifecycle/behavior]
            {foreach}
                @record
                .{UserSetting/volumeSettingsTimeouts}
            .{as}
                timeout
            .{do}
                {Browser/clearTimeout}
                    @timeout
            {Browser/clearTimeout}
                @record
                .{UserSetting/globalSettingsTimeout}
`;
