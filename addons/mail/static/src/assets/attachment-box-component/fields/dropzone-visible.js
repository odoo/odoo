/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            dropzoneVisible
        [Field/model]
            AttachmentBoxComponent
        [Field/type]
            one
        [Field/target]
            DropzoneVisibleComponentHook
`;
