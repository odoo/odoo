/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            part1
        [Element/model]
            ComposerSuggestionComponent
        [web.Element/class]
            text-truncate
        [web.Element/style]
            {Dev/comment}
                avoid shrinking part 1 because it is more important than part 2
                because no shrink, ensure it cannot overflow with a max-width
            [web.scss/flex]
                0
                0
                auto
            [web.scss/max-width]
                {scss/map-get}
                    {scss/$sizes}
                    100
            [web.scss/padding-inline-end]
                {scss/map-get}
                    {scss/$spacers}
                    2
            [web.scss/font-weight]
                {scss/$font-weight-bold}
`;
