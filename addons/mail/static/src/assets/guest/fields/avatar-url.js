/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            avatarUrl
        [Field/model]
            Guest
        [Field/type]
            attr
        [Field/target]
            String
        [Field/compute]
            /web/image/mail.guest/
            .{+}
                @record
                .{Guest/id}
            .{+}
                /avatar_128?unique=
            .{+}
                @record
                .{Guest/name}
`;
