/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        FIXME: dependent on implementation that uses arbitrary order in relations!!
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            allOrdered
        [Field/model]
            ChatWindowManager
        [Field/type]
            many
        [Field/target]
            ChatWindow
        [Field/compute]
            @record
            .{ChatWindowManager/chatWindows}
`;
