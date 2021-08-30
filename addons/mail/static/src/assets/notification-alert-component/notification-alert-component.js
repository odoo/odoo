/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Model
        [Model/name]
            NotificationAlertComponent
        [Model/template]
            root
                text
        [Model/actions]
            NotificationAlertComponent/isNotificationBlocked
`;
