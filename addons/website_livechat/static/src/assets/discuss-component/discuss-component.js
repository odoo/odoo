/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            ModelAddon
        [ModelAddon/feature]
            website_livechat
        [ModelAddon/model]
            DiscussComponent
        [ModelAddon/template]
            root
                visitorBanner
`;
