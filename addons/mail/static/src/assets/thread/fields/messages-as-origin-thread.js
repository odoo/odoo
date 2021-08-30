/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        All messages that have been originally posted in this thread.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            messagesAsOriginThread
        [Field/model]
            Thread
        [Field/type]
            many
        [Field/target]
            Message
        [Field/inverse]
            Message/originThread
        [Field/isCausal]
            true
`;
