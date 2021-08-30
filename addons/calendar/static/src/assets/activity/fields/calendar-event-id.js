/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/feature]
            calendar
        [Field/name]
            calendarEventId
        [Field/model]
            Activity
        [Field/type]
            attr
        [Field/target]
            Number
        [Field/default]
            false
`;
