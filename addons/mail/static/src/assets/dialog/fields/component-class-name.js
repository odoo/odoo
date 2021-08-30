/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            componentClassName
        [Field/model]
            Dialog
        [Field/type]
            attr
        [Field/target]
            String
        [Field/compute]
            {if}
                @record
                .{Dialog/attachmentDeleteConfirmView}
            .{then}
                o_Dialog_componentMediumSize
                align-self-start
                mt-5
            .{elif}
                @record
                .{Dialog/deleteMessageConfirmView}
            .{then}
                o_Dialog_componentLargeSize
                align-self-start
                mt-5
            .{else}
                {String/empty}
`;
