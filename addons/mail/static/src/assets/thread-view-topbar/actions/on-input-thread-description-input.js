/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Handles input on the "thread description" input of this top bar.
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            ThreadViewTopbar/onInputThreadDescriptionInput
        [Action/params]
            ev
                [type]
                    web.InputEvent
            record
                [type]
                    ThreadViewTopbar
        [Action/behavior]
            {Record/update}
                [0]
                    @record
                [1]
                    [ThreadViewTopbar/pendingThreadDescription]
                        @ev
                        .{web.Event/target}
                        .{web.Element/value}
`;
