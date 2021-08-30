/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            managerAsNewMessage
        [Field/model]
            ChatWindow
        [Field/type]
            one
        [Field/target]
            ChatWindowManager
        [Field/inverse]
            ChatWindowManager/newMessageChatWindow
        [Field/isReadonly]
            true
`;
