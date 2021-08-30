/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            visibleOffset
        [Field/model]
            ChatWindow
        [Field/type]
            attr
        [Field/target]
            Number
        [Field/compute]
            {if}
                @record
                .{ChatWindow/manager}
                .{isFalsy}
            .{then}
                0
                {break}
            {if}
                @record
                .{ChatWindow/manager}
                .{ChatWindowManager/visual}
                .{Visual/visible}
                .{Collection/includes]
                    @record
            .{then}
                0
                {break}
            @record
            .{ChatWindow/manager}
            .{ChatWindowManager/visual}
            .{Visual/visible}
            .{Collection/indexOf]
                @record
            .{Visible/offset}
`;
