/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Serves as compute dependency.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            threadIsLoadingAttachments
        [Field/model]
            Chatter
        [Field/type]
            attr
        [Field/related]
            Chatter/thread
            Thread/isLoadingAttachments
`;
