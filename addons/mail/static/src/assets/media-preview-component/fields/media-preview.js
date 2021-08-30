/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            mediaPreview
        [Field/model]
            MediaPreviewComponent
        [Field/type]
            one
        [Field/target]
            MediaPreview
`;
