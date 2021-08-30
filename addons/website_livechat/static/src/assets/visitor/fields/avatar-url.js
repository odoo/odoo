/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Url to the avatar of the visitor.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            avatarUrl
        [Field/model]
            Visitor
        [Field/type]
            attr
        [Field/target]
            String
        [Field/compute]
            {if}
                @record
                .{Visitor/partner}
                .{isFalsy}
            .{then}
                /mail/static/src/img/smiley/avatar.jpg
            .{else}
                @record
                .{Visitor/partner}
                .{Partner/avatarUrl}
`;
