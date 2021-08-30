/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            ModelAddon
        [ModelAddon/model]
            Env
        [ModelAddon/feature]
            im_livechat
        [ModelAddon/fields]
            pinnedLivechats
`;
