/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            backgroundOpacity
        [Field/model]
            Dialog
        [Field/type]
            attr
        [Field/target]
            Float
        [Field/compute]
            {if}
                @record
                .{Dialog/attachmentViewer}
            .{then}
                0.7
            .{else}
                0.5
`;
