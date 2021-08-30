/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            UserSetting/setPushToTalkKey
        [Action/params]
            ev
                [type]
                    web.Event
            record
                [type]
                    UserSetting
        [Action/behavior]
            {Record/update}
                [0]
                    @record
                [1]
                    [UserSetting/pushToTalkKey]
                        @ev
                        .{web.Event/shiftKey}
                        .{+}
                            .
                        .{+}
                            @ev
                            .{web.Event/ctrlKey}
                            .{|}
                                @ev
                                .{web.Event/metaKey}
                        .{+}
                            .
                        .{+}
                            @ev
                            .{web.Event/altKey}
                        .{+}
                            .
                        .{+}
                            @ev
                            .{web.Event/key}
            {if}
                {Env/isCurrentUserGuest}
                .{isFalsy}
            .{then}
                {UserSetting/_saveSettings}
                    @record
`;
