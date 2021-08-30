/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Determines the dialog displaying this attachment viewer.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            dialogOwner
        [Field/model]
            AttachmentViewer
        [Field/type]
            one
        [Field/target]
            Dialog
        [Field/isCausal]
            true
        [Field/isReadonly]
            true
        [Field/inverse]
            Dialog/attachmentViewer
`;
