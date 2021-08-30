/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Handles keydown on the "thread description" input of this top bar.
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            ThreadViewTopbar/onKeyDownThreadDescriptionInput
        [Action/params]
            ev
                [type]
                    web.KeyboardEvent
            record
                [type]
                    ThreadViewTopbar
        [Action/behavior]
            {switch}
                @ev
                .{web.KeyboardEvent/key}
            .{case}
                [Enter]
                    {ThreadViewTopbar/_applyThreadChangeDescription}
                        @record
                [Escape]
                    {ThreadViewTopbar/_discardThreadChangeDescription}
                        @record
`;
