/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Determines the name of 'this'. It serves as visual clue when
        displaying 'this', and also serves as default partner name when
        creating a new partner from 'this'.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            name
        [Field/model]
            SuggestedRecipientInfo
        [Field/type]
            attr
        [Field/target]
            String
        [Field/compute]
            {if}
                @record
                .{SuggestedRecipientInfo/partner}
                .{&}
                    @record
                    .{SuggestedRecipientInfo/partner}
                    .{Partner/nameOrDisplayName}
            .{then}
                @record
                .{SuggestedRecipientInfo/partner}
                .{Partner/nameOrDisplayName}
            .{else}
                @record
                .{SuggestedRecipientInfo/name}
`;
