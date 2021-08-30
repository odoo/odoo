/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Link with a composer view to handle attachments.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            composerViewOwner
        [Field/model]
            AttachmentList
        [Field/type]
            one
        [Field/target]
            ComposerView
        [Field/isReadonly]
            true
        [Field/inverse]
            ComposerView/attachmentList
`;
