/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            nameOrDisplayName
        [Field/model]
            User
        [Field/type]
            attr
        [Field/target]
            String
        [Field/compute]
            {if}
                @record
                .{User/partner}
                .{&}
                    @record
                    .{User/partner}
                    .{Partner/nameOrDisplayName}
            .{then}
                @record
                .{User/partner}
                .{Partner/nameOrDisplayName}
            .{else}
                @record
                .{User/displayName}
`;
