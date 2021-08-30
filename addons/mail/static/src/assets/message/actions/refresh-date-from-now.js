/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Refreshes the value of 'dateFromNow' field to the "current now".
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            Message/refreshDateFromNow
        [Action/params]
            message
                [type]
                    Message
        [Action/behavior]
            {Record/update}
                [0]
                    @message
                [1]
                    [Message/dateFromNow]
                        {Message/_computeDateFromNow}
                            @message
`;
