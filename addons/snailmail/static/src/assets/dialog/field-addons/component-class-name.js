/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            FieldAddon
        [FieldAddon/feature]
            snailmail
        [FieldAddon/name]
            componentClassName
        [Field/model]
            Dialog
        [FieldAddon/compute]
            {if}
                @record
                .{Dialog/snailmailErrorView}
            .{then}
                o_Dialog_componentMediumSize
                align-self-start
                mt-5
            .{else}
                @original
`;
