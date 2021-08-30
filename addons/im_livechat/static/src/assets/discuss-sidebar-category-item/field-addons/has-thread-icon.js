/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            FieldAddon
        [FieldAddon/field]
            DiscussSidebarCategoryItem/hasThreadIcon
        [FieldAddon/feature]
            im_livechat
        [FieldAddon/compute]
            {if}
                @record
                .{DiscussSidebarCategoryItem/channelType}
                .{=}
                    livechat
            .{then}
                false
            .{else}
                @original
`;
