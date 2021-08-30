/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            messages
        [Field/model]
            Attachment
        [Field/type]
            many
        [Field/target]
            Message
        [Field/inverse]
            Message/attachments
`;
