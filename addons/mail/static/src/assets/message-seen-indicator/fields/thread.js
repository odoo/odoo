/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        The thread concerned by this seen indicator.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            thread
        [Field/model]
            MessageSeenIndicator
        [Field/type]
            one
        [Field/target]
            Thread
        [Field/isReadonly]
            true
        [Field/isRequired]
            true
        [Field/inverse]
            MessageSeenIndicator/messageSeenIndicators
`;
