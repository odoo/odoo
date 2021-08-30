/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            ModelAddon
        [ModelAddon/feature]
            calendar
        [ModelAddon/model]
            Activity
        [ModelAddon/fields]
            calendarEventId
        [ModelAddon/actions]
            Activity/reschedule
        [ModelAddon/actionAddons]
            Activity/convertData
            Activity/deleteServerRecord
`;
