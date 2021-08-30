/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            WelcomeView/getNextGuestNameInputId
        [Action/returns]
            Integer
        [Action/behavior]
            {Record/update}
                [0]
                    @env
                [1]
                    [Env/nextGuestNameInputId]
                        {Env/nextGuestNameInputId}
                        .{+}
                            1
            {Env/nextGuestNameInputId}
`;
