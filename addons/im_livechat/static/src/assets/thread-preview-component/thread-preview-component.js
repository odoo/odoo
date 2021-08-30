/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            ModelAddon
        [ModelAddon/feature]
            im_livechat
        [ModelAddon/model]
            ThreadPreviewComponent
        [ModelAddon/actionAddons]
            ThreadPreviewComponent/getImage
`;
