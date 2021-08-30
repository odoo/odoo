/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            originThread
        [Field/model]
            Attachment
        [Field/type]
            one
        [Field/target]
            Thread
        [Field/inverse]
            Thread/originThreadAttachments
`;
