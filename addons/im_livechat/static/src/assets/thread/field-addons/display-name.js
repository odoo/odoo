/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            FieldAddon
        [FieldAddon/field]
            Thread/displayName
        [FieldAddon/feature]
            im_livechat
        [FieldAddon/compute]
            {if}
                @record
                .{Thread/channelType}
                .{=}
                    livechat
                .{&}
                    @record
                    .{Thread/correspondent}
            .{then}
                {if}
                    @record
                    .{Thread/correspondent}
                    .{Partner/country}
                .{then}
                    @record
                    .{Thread/correspondent}
                    .{Partner/nameOrDisplayName}
                    .{+}
                            (
                    .{+}
                        @record
                        .{Thread/correspondent}
                        .{Partner/country}
                        .{Country/name}
                    .{+}
                        )
                .{else}
                    @record
                    .{Thread/correspondent}
                    .{Partner/nameOrDisplayName}
            .{else}
                @original
`;
