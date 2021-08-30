/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Deprecated.
        States the 'displayName' of this partner, as returned by the server.
        The value of this field is unreliable (notably its value depends on
        context on which it was received) therefore it should only be used as
        a default if the actual 'name' is missing (@see 'nameOrDisplayName').
        And if a specific name format is required, it should be computed from
        relevant fields instead.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            displayName
        [Field/model]
            Partner
        [Field/type]
            attr
        [Field/target]
            String
        [Field/compute]
            @record
            .{Partner/displayName}
            .{|}
                @record
                .{Partner/user}
                .{&}
                    @record
                    .{Partner/user}
                    .{User/displayName}
`;
