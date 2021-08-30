/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Model
        [Model/name]
            DiscussSidebarComponent
        [Model/fields]
            discussView
        [Model/template]
            root
                startMeetingButtonContainer
                    startMeetingButton
                separator1
                categoryMailbox
                    mailboxInbox
                    mailboxStarred
                    mailboxHistory
                separator2
                quickSearch
                categoryChannel
                categoryChat
        [Model/lifecycles]
            onUpdate
`;
