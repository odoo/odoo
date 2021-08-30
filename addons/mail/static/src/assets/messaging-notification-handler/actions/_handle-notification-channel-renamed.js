/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            MessagingNotificationHandler/_handleNotificationChannelRenamed
        [Action/params]
            notificationHandler
                [type]
                    MessagingNotificationHandler
            id
                [type]
                    integer
            name
                [type]
                    String
        [Action/behavior]
            {Record/insert}
                [Record/models]
                    Thread
                [Thread/id]
                    @id
                [Thread/model]
                    mail.channel
                [Thread/name]
                    @name
`;
