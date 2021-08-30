/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            WelcomeView/onClickJoinButton
        [Action/params]
            ev
                [type]
                    MouseEvent
            record
                [type]
                    WelcomeView
        [Action/behavior]
            {WelcomeView/joinChannel}
                @record
`;
