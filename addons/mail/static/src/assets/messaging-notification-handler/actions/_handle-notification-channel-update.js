/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            MessagingNotificationHandler/_handleNotificationChannelUpdate
        [Action/params]
            channelData
                [type]
                    Object
        [Action/behavior]
            {Record/insert}
                [Record/models]
                    Thread
                [Thread/model]
                    mail.channel
                @channelData
`;
