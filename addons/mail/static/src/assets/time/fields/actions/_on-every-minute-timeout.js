/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            Time/_onEveryMinuteTimeout
        [Action/behavior]
            {Record/update}
                [0]
                    {Env/time}
                [1]
                    [Time/currentDateEveryMinute]
                        {Record/insert}
                            [Record/models]
                                Date
`;
