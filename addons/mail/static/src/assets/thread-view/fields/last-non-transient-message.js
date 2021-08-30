/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Serves as compute dependency.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            lastNonTransientMessage
        [Field/model]
            ThreadView
        [Field/type]
            one
        [Field/target]
            Message
        [Field/related]
            ThreadView/thread
            Thread/lastNonTransientMessage
`;
