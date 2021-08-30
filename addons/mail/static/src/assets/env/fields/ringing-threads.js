/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Threads for which the current partner has a pending invitation.
        It is computed from the inverse relation for performance reasons.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            ringingThreads
        [Field/model]
            Env
        [Field/type]
            many
        [Field/target]
            Thread
        [Field/inverse]
            Thread/messagingAsRingingThread
`;
