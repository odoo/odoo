/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            ThreadViewTopbar/onKeyDownThreadNameInput
        [Action/params]
            record
                [type]
                    ThreadViewTopbar
            ev
                [type]
                    web.KeyboardEvent
        [Action/behavior]
            {switch}
                @ev
                .{web.KeyboardEvent/key}
            .{case}
                [Enter]
                    {ThreadViewTopbar/_applyThreadRename}
                        @record
                [Escape]
                    {ThreadViewTopbar/_discardThreadRename}
                        @record
`;
