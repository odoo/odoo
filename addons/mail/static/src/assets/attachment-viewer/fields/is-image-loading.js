/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Determine whether the image is loading or not. Useful to diplay
        a spinner when loading image initially.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            isImageLoading
        [Field/model]
            AttachmentViewer
        [Field/type]
            attr
        [Field/target]
            Boolean
        [Field/default]
            false
`;
