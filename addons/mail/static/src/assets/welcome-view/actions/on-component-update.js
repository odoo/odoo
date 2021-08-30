/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Handles OWL update on this WelcomeView component.
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            WelcomeView/onComponentUpdate
        [Action/params]
            record
                [type]
                    WelcomeView
        [Action/behavior]
            {WelcomeView/_handleFocus}
                @record
`;
