/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Counts how many drag enter/leave happened on self and children. This
        ensures the drop effect stays active when dragging over a child.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            _dragCount
        [Field/model]
            DropZoneComponent
        [Field/type]
            attr
        [Field/target]
            Number
        [Field/default]
            0
`;
