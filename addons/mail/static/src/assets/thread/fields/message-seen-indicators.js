/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Contains the message fetched/seen indicators for all messages of this thread.
        FIXME This field should be readonly once task-2336946 is done.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            messageSeenIndicators
        [Field/model]
            Thread
        [Field/type]
            many
        [Field/target]
            MessageSeenIndicator
        [Field/inverse]
            MessageSeenIndicator/thread
        [Field/isCausal]
            true
`;
