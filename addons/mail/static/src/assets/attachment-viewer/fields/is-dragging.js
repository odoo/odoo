/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Determine whether the user is currently dragging the image.
        This is useful to determine whether a click outside of the image
        should close the attachment viewer or not.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            isDragging
        [Field/model]
            AttachmentViewer
        [Field/type]
            attr
        [Field/target]
            Boolean
        [Field/default]
            false
`;
