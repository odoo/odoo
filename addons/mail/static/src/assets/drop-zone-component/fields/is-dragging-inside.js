/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Determine whether the user is dragging files over the dropzone.
        Useful to provide visual feedback in that case.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            isDraggingInside
        [Field/model]
            DropZoneComponent
        [Field/type]
            attr
        [Field/target]
            Boolean
        [Field/default]
            false
`;
