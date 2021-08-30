/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            part2
        [Element/model]
            ComposerSuggestionComponent
        [web.Element/class]
            text-truncate
        [web.Element/style]
            {Dev/comment}
                shrink part 2 to properly ensure it cannot overflow
            [web.scss/flex]
                0
                1
                auto
            [web.scss/font-style]
                italic
            [web.scss/color]
                {scss/$gray-600}
`;
