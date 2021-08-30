/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            FieldAddon
        [FieldAddon/feature]
            snailmail
        [FieldAddon/name]
            record
        [Field/model]
            Dialog
        [FieldAddon/compute]
            {if}
                @record
                .{Dialog/snailmailErrorView}
            .{then}
                @record
                .{Dialog/snailmailErrorView}
            .{else}
                @original
`;
