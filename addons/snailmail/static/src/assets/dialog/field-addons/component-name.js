/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            FieldAddon
        [FieldAddon/feature]
            snailmail
        [FieldAddon/name]
            componentName
        [Field/model]
            Dialog
        [FieldAddon/compute]
            {if}
                @record
                .{Dialog/snailmailErrorView}
            .{then}
                SnailmailError
            .{else}
                @original
`;
