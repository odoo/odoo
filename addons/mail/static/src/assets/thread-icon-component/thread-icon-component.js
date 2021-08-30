/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Model
        [Model/name]
            ThreadIconComponent
        [Model/fields]
            thread
        [Model/template]
            root
                channelPrivate
                channelPublic
                channelGroups
                typingChat
                onlineIcon
                offlineIcon
                awayIcon
                botIcon
                noImStatus
                groupIcon
                mailboxInbox
                mailboxStarred
                mailboxHistory
`;
