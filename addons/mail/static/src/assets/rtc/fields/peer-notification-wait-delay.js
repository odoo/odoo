/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Determines the delay to wait (in ms) before sending peer
        notifications to the server. Sending many notifications at once
        significantly increase the connection time because the server can't
        handle too many requests at once, but handles much faster one bigger
        request, even with a delay. The delay should however not be too high.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            peerNotificationWaitDelay
        [Field/model]
            Rtc
        [Field/type]
            attr
        [Field/target]
            Integer
        [Field/isCausal]
            50
`;
