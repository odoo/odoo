/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        States whether 'this' is visible or not. Should be considered
        read-only. Setting this value manually will not make it visible.
        @see 'ChatWindow/makeVisible'
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            isVisible
        [Field/model]
            ChatWindow
        [Field/type]
            attr
        [Field/target]
            Boolean
        [Field/compute]
            {if}
                @record
                .{ChatWindow/manager}
                .{isFalsy}
            .{then}
                false
            .{else}
                @record
                .{ChatWindow/manager}
                .{ChatWindowManager/allOrderedVisible}
                .{Collection/includes}
                    @record
`;
