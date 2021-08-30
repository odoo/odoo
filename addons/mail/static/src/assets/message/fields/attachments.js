/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            attachments
        [Field/model]
            Message
        [Field/type]
            many
        [Field/target]
            Attachment
        [Field/inverse]
            Attachment/messages
`;
