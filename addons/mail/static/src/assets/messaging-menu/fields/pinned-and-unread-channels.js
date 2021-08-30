/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        States all the pinned channels that have unread messages.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            pinnedAndUnreadChannels
        [Field/model]
            MessagingMenu
        [Field/type]
            many
        [Field/target]
            Thread
        [Field/isReadonly]
            true
        [FIeld/inverse]
            Thread/messagingMenuAsPinnedAndUnreadChannel
`;
