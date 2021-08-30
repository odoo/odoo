/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            ActionAddon
        [ActionAddon/action]
            MessagingInitializer/start
        [ActionAddon/feature]
            mail_bot
        [ActionAddon/params]
            messagingInitializer
        [ActionAddon/behavior]
            {Record/doAsync}
                []
                    @messagingInitializer
                []
                    @original
            {if}
                {Env/isOdoobotInitialized}
                .{isFalsy}
            .{then}
                {MessagingInitializer/_initializeOdoobot}
`;
