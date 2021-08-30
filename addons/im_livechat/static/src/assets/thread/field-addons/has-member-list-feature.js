/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            FieldAddon
        [FieldAddon/field]
            hasMemberListFeature
        [FieldAddon/model]
            Thread
        [FieldAddon/feature]
            im_livechat
        [FieldAddon/compute]
            {if}
                @record
                .{Thread/channelType}
                .{=}
                    livechat
            .{then}
                true
            .{else}
                @original
`;
