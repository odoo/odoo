/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Country of the visitor.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            country
        [Field/model]
            Visitor
        [Field/type]
            one
        [Field/target]
            Country
        [Field/compute]
            {if}
                @record
                .{Visitor/partner}
                .{&}
                    @record
                    .{Visitor/partner}
                    .{Partner/country}
            .{then}
                @record
                .{Visitor/partner}
                .{Partner/country}
            .{elif}
                @record
                .{Visitor/country}
            .{then}
                @record
                .{Visitor/country}
            .{else}
                {Record/empty}
`;
