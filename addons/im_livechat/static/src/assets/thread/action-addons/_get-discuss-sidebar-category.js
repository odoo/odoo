/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            ActionAddon
        [ActionAddon/action]
            Thread/_getDiscussSidebarCategory
        [ActionAddon/feature]
            im_livechat
        [ActionAddon/behavior]
            {switch}
                @record
                .{Thread/channelType}
            .{case}
                [livechat]
                    {Discuss/categoryLivechat}
                []
                    @original
`;
