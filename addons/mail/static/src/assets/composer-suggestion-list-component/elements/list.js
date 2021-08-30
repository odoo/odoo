/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            list
        [Element/model]
            ComposerSuggestionListComponent
        [web.Element/class]
            dropdown-menu
            show
        [web.Element/style]
            {Dev/comment}
                prevent suggestion items from overflowing
            [web.scss/width]
                {scss/map-get}
                    {scss/$sizes}
                    100
            {Dev/comment}
                prevent from overflowing chat window, must be smaller than its height
                minus the max height taken by composer and attachment list
            [web.scss/max-height]
                150
                px
            [web.scss/overflow]
                auto
`;
