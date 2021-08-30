/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            coreMain
        [Element/model]
            ComposerViewComponent
        [web.Element/style]
            [web.scss/grid-area]
                core-main
            [web.scss/min-width]
                0
            [web.scss/display]
                flex
            [web.scss/flex-wrap]
                nowrap
            [web.scss/align-items]
                flex-start
            [web.scss/flex]
                1
                1
                auto
            {if}
                @record
                .{ComposerViewComponent/isCompact}
                .{isFalsy}
            .{then}
                [web.scss/flex-direction]
                    column
                [web.scss/background]
                    {scss/$white}
                [web.scss/border]
                    {scss/$border-width}
                    solid
                    {scss/$border-color}
                [web.scss/border-radius]
                    {scss/$o-mail-rounded-rectangle-border-radius-lg}
`;
