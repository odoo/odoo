/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        The message concerned by this seen indicator.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            message
        [Field/model]
            MessageSeenIndicator
        [Field/type]
            one
        [Field/target]
            Message
        [Field/inReadonly]
            true
`;
