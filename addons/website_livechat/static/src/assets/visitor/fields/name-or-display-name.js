/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            nameOrDisplayName
        [Field/model]
            Visitor
        [Field/type]
            attr
        [Field/target]
            String
        [Field/compute]
            {if}
                @record
                .{Visitor/partner}
            .{then}
                @record
                .{Visitor/partner}
                .{Partner/nameOrDisplayName}
            .{else}
                @record
                .{Visitor/displayName}
`;
