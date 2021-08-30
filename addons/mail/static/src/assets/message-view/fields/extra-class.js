/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Determines which extra class this message view component should have.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            extraClass
        [Field/model]
            MessageView
        [Field/type]
            attr
        [Field/target]
            String
        [Field/default]
            {String/empty}
        [Field/compute]
            {if}
                @record
                .{MessageView/threadView}
            .{then}
                o_MessageList_item
                o_MessageList_message
            .{else}
                {Record/empty}
`;
