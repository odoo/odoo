/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            ModelAddon
        [ModelAddon/feature]
            im_livechat
        [ModelAddon/model]
            Partner
        [ModelAddon/fields]
            livechatUsername
        [ModelAddon/actions]
            Partner/getNextPublicId
        [ModelAddon/actionAddons]
            Partner/convertData
`;
