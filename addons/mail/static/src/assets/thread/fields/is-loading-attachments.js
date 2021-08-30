/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        States whether 'this' is currently loading attachments.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            isLoadingAttachments
        [Field/model]
            Thread
        [Field/type]
            attr
        [Field/target]
            Boolean
        [Field/default]
            false
`;
