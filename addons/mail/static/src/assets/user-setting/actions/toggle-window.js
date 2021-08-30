/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        toggles the display of the option window
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            UserSetting/toggleWindow
        [Action/params]
            record
                [type]
                    UserSetting
        [Action/behavior]
            {Record/update}
                [0]
                    @record
                [1]
                    [UserSetting/isOpen]
                        @record
                        .{UserSetting/isOpen}
                        .{isFalsy}
`;
