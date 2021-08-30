/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Determine whether current user is currently adding a chat from
        the sidebar.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            isAddingChat
        [Field/model]
            Discuss
        [Field/type]
            attr
        [Field/target]
            Boolean
        [Field/default]
            false
        [Field/compute]
            {if}
                @record
                .{Discuss/discussView}
                .{isFalsy}
            .{then}
                false
            .{else}
                @record
                .{Discuss/isAddingChat}
`;
