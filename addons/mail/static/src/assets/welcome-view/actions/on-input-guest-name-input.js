/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            WelcomeView/onInputGuestNameInput
        [Action/params]
            ev
                [type]
                    KeyboardEvent
            record
                [type]
                    WelcomeView
        [Action/behavior]
            {WelcomeView/_updateGuestNameWithInputValue}
                @record
`;
