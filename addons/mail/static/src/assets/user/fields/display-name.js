/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            displayName
        [Field/model]
            User
        [Field/type]
            attr
        [Field/target]
            String
        [Field/compute]
            @record
            .{User/displayName}
            .{|}
                @record
                .{User/partner}
                .{&}
                    @record
                    .{User/partner}
                    .{Partner/displayName}
`;
