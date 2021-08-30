/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Determines whether 'this' will be added to recipients when posting a
        new message on 'this.thread'.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            isSelected
        [Field/model]
            SuggestedRecipientInfo
        [Field/type]
            attr
        [Field/target]
            Boolean
        [Field/default]
            true
        [Field/compute]
            {Dev/comment}
                Prevents selecting a recipient that does not have a partner.
            {if}
                @record
                .{SuggestedRecipientInfo/partner}
            .{then}
                @record
                .{SuggestedRecipientInfo/isSelected}
            .{else}
                false
`;
