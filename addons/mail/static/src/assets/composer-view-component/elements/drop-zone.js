/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            dropZone
        [Element/model]
            ComposerViewComponent
        [Field/target]
            DropZoneComponent
        [Element/isPresent]
            @record
            .{ComposerViewComponent/dropzoneVisible}
            .{DropzoneVisibleComponentHook/value}
`;
