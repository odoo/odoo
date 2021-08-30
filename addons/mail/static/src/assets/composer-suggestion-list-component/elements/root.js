/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            root
        [Element/model]
            ComposerSuggestionListComponent
        [web.Element/style]
            [web.scss/position]
                absolute
            {Dev/comment}
                prevent suggestion items from overflowing
            [web.scss/width]
                {scss/map-get}
                    {scss/$sizes}
                    100
            {if}
                @record
                .{ComposerSuggestionListComponent/isBelow}
            .{then}
                [web.scss/bottom]
                    0
`;
