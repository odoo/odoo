/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            FieldAddon
        [FieldAddon/field]
            Thread/isChatChannel
        [FieldAddon/model]
            Thread
        [FieldAddon/feature]
            im_livechat
        [FieldAddon/compute]
            @record
            .{Thread/channelType}
            .{=}
                livechat
            .{|}
                @original
`;
