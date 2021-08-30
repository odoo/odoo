/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        States on which composer this attachment is currently being created.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            composer
        [Field/model]
            Attachment
        [Field/type]
            one
        [Field/target]
            Composer
        [Field/inverse]
            Composer/attachments
`;
