/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            drop
        [Element/model]
            ComposerSuggestionListComponent
        [web.Element/class]
            {if}
                @record
                .{ComposerSuggestionListComponent/isBelow}
            .{then}
                dropdown
            {if}
                @record
                .{ComposerSuggestionListComponent/isBelow}
                .{isFalsy}
            .{then}
                dropup
        [web.Element/style]
            {Dev/comment}
                prevent suggestion items from overflowing
            [web.scss/width]
                {scss/map-get}
                    {scss/$sizes}
                    100
`;
