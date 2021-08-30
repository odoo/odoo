/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Model
        [Model/name]
            Guest
        [Model/fields]
            authoredMessages
            avatarUrl
            id
            name
            rtcSessions
            volumeSetting
        [Model/id]
            Guest/id
        [Model/actions]
            Guest/performRpcGuestUpdateName
`;
