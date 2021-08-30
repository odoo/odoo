/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Origin thread of this message (if any).
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            originThread
        [Field/model]
            Message
        [Field/type]
            one
        [Field/target]
            Thread
        [Field/inverse]
            Thread/messagesAsOriginThread
`;
