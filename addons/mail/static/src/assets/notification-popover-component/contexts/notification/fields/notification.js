/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            notification
        [Field/model]
            NotificationPopoverComponent:notification
        [Field/type]
            one
        [Field/target]
            Notification
        [Field/isRequired]
            true
`;
