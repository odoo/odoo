/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Model
        [Model/name]
            Time
        [Model/id]
            Time/env
        [Model/fields]
            currentDateEveryMinute
            everyMinuteIntervalId
        [Model/actions]
            Time/_onEveryMinuteTimeout
        [Model/lifecycles]
            onDelete
`;
