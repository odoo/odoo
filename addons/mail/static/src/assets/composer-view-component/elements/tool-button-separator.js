/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            toolButtonSeparator
        [Element/model]
            ComposerViewComponent
        [Element/isPresent]
            @record
            .{ComposerViewComponent/isCompact}
        [web.Element/style]
            [web.scss/flex]
                0
                0
                auto
            [web.scss/margin-top]
                {scss/map-get}
                    {scss/$spacers}
                    2
            [web.scss/margin-bottom]
                {scss/map-get}
                    {scss/$spacers}
                    2
            [web.scss/border-left]
                {scss/$border-width}
                solid
                {scss/$border-color}
`;
