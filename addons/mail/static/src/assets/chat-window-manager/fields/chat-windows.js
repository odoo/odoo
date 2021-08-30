/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            chatWindows
        [Field/model]
            ChatWindowManager
        [Field/type]
            many
        [Field/target]
            ChatWindow
        [Field/inverse]
            ChatWindow/manager
        [Field/isCausal]
            true
`;
