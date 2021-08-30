/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Updates 'pendingGuestName' with the value of the input element
        referred by 'guestNameInputRef'.
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            WelcomeView/_updateGuestNameWithInputValue
        [Action/params]
            record
                [type]
                    WelcomeView
        [Action/behavior]
            {Record/update}
                [0]
                    @record
                [1]
                    [WelcomeView/pendingGuestName]
                        @record
                        .{WelcomeView/guestNameInputRef}
                        .{web.Element/value}
`;
