/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            ThreadViewTopbar/onInputGuestNameInput
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
                    [ThreadViewTopbar/pendingGuestName]
                        @record
                        .{ThreadViewTopbar/guestNameInputRef}
                        .{web.Element/value}
`;
