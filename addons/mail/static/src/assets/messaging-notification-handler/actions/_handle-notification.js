/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            MessagingNotificationHandler/_handleNotification
        [Action/params]
            record
                [type]
                    MessagingNotificationHandler
            message
                [type]
                    Object
        [Action/behavior]
`;
