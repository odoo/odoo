/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            displayName
        [Field/model]
            Attachment
        [Field/type]
            attr
        [Field/target]
            String
        [Field/compute]
            {if}
                @record
                .{Attachment/name}
            .{then}
                @record
                .{Attachment/name}
            .{elif}
                @record
                .{Attachment/filename}
            .{then}
                @record
                .{Attachment/filename}
            .{else}
                {Record/empty}
`;
