/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Determines the bus that is used to communicate messaging events.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            messagingBus
        [Field/model]
            Env
        [Field/type]
            one
        [Field/target]
            EventBus
        [Field/isRequired]
            true
        [Field/isReadonly]
            true
        [Field/default]
            {Record/insert}
                [Record/models]
                    EventBus
`;
