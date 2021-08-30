/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            nameOrDisplayName
        [Field/model]
            Partner
        [Field/type]
            attr
        [Field/target]
            String
        [Field/compute]
            @record
            .{Partner/name}
            .{|}
                @record
                .{Partner/displayName}
`;
