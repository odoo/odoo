/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            newMessageChatWindow
        [Field/model]
            ChatWindowManager
        [Field/type]
            one
        [Field/target]
            ChatWindow
        [Field/isCausal]
            true
        [Field/inverse]
            ChatWindow/managerAsNewMessage
`;
