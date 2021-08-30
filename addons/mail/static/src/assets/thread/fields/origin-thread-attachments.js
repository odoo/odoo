/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            originThreadAttachments
        [Field/model]
            Thread
        [Field/type]
            many
        [Field/target]
            Attachment
        [Field/inverse]
            originThread
        [Field/isCausal]
            true
`;
