/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Determiners whether the attachment box is visible initially.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            isAttachmentBoxVisibleInitially
        [Field/model]
            Chatter
        [Field/type]
            attr
        [Field/target]
            Boolean
        [Field/default]
            false
`;
