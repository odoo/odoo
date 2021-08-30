/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            UserSetting/pushToTalkKeyToString
        [Action/params]
            record
                [type]
                    UserSetting
        [Action/returns]
            String
        [Action/behavior]
            :res
                {UserSetting/pushToTalkKeyFormat}
                    @record
            {if}
                @res
                .{Dict/get}
                    ctrlKey
            .{then}
                Ctrl + 
            {if}
                @res
                .{Dict/get}
                    altKey
            .{then}
                Alt + 
            {if}
                @res
                .{Dict/get}
                    shiftKey
            .{then}
                Shift + 
            @res
            .{Dict/get}
                key
`;
