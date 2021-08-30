/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            authorName
        [Field/model]
            Message
        [Field/type]
            attr
        [Field/target]
            String
        [Field/compute]
            {if}
                @record
                .{Message/author}
            .{then}
                @record
                .{Message/author}
                .{Partner/nameOrDisplayName}
            .{elif}
                @record
                .{Message/guestAuthor}
            .{then}
                @record
                .{Message/guestAuthor}
                .{Guest/name}
            .{elif}
                @record
                .{Message/emailFrom}
            .{then}
                @record
                .{Message/emailFrom}
            .{else}
                {Locale/text}
                    Anonymous
`;
