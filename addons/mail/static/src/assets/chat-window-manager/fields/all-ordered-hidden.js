/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            allOrderedHidden
        [Field/model]
            ChatWindowManager
        [Field/type]
            many
        [Field/target]
            ChatWindow
        [Field/compute]
            @record
            .{ChatWindowManager/visual}
            .{Visual/hidden}
            .{Hidden/chatWindows}
`;
