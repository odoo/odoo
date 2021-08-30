/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        States the OWL component of this attachment image.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            component
        [Field/model]
            AttachmentImage
        [Field/type]
            attr
        [Field/target]
            AttachmentListComponent
`;
