/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            ModelAddon
        [ModelAddon/feature]
            mail_bot
        [ModelAddon/model]
            MessagingInitializer
        [ModelAddon/actions]
            MessagingInitializer/_initializeOdoobot
        [ModelAddon/actionAddons]
            MessagingInitializer/start
`;
