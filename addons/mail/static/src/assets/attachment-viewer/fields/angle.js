/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Angle of the image. Changes when the user rotates it.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            angle
        [Field/model]
            AttachmentViewer
        [Field/type]
            attr
        [Field/target]
            Number
        [Field/default]
            0
`;
