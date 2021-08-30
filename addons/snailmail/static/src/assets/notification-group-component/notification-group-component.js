/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            ModelAddon
        [ModelAddon/feature]
            snailmail
        [ModelAddon/model]
            NotificationGroupComponent
        [ModelAddon/elementAddons]
            inlineText
        [ModelAddon/actionAddons]
            NotificationGroupComponent/getImage
`;
