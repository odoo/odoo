/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            avatarUrl
        [Field/model]
            Partner
        [Field/type]
            attr
        [Field/target]
            String
        [Field/compute]
            {if}
                @record
                .{=}
                    {Env/partnerRoot}
            .{then}
                /mail/static/src/img/odoobot.png
            .{else}
                /web/image/res.partner/
                .{+}
                    @record
                    .{Partner/id}
                .{+}
                    /avatar_128
`;
