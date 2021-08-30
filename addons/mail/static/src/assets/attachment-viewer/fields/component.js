/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        States the OWL component of this attachment viewer.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            component
        [Field/model]
            AttachmentViewer
        [Field/type]
            attr
        [Field/target]
            AttachmentViewerComponent
        [Field/inverse]
            AttachmentViewerComponent/attachmentViewer
`;
