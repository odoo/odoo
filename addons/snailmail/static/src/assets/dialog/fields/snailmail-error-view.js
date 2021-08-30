/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/feature]
            snailmail
        [Field/name]
            snailmailErrorView
        [Field/model]
            Dialog
        [Field/type]
            one
        [Field/target]
            SnailmailErrorView
        [Field/isCausal]
            true
        [Field/inverse]
            SnailmailErrorView/dialogOwner
        [Field/compute]
            {if}
                @record
                .{Dialog/messageViewOwnerAsSnailmailError}
            .{then}
                {Record/insert}
                    [Record/models]
                        SnailmailErrorView
            .{else}
                {Record/empty}
`;
