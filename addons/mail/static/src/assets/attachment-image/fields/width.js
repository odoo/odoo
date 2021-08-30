/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Returns an arbitrary high value, this is effectively a max-width and
        the height should be more constrained.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            width
        [Field/model]
            AttachmentImage
        [Field/type]
            attr
        [Field/target]
            Integer
        [Field/isRequired]
            true
        [Field/compute]
            1920
`;
