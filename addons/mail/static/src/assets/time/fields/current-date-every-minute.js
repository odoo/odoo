/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Contains a Date object that is set to the current time, and is
        (re-)computed every minute.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            currentDateEveryMinute
        [Field/model]
            Time
        [Field/type]
            attr
        [Field/target]
            Date
        [Field/default]
            {Record/insert}
                [Record/models]
                    Date
`;
