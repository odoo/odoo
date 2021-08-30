/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            ModelAddon
        [ModelAddon/feature]
            im_livechat
        [ModelAddon/model]
            MessagingInitializer
        [ModelAddon/actionAddons]
            MessagingInitializer/_initCommands
            MessagingInitializer/_initResUsersSettings
`;
