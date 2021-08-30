/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            ModelAddon
        [ModelAddon/feature]
            snailmail
        [ModelAddon/model]
            NotificationGroup
        [ModelAddon/actionAddons]
            NotificationGroup/_openDocuments
            NotificationGroup/openCancelAction
`;
