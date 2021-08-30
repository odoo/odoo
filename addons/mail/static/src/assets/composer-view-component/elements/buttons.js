/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            buttons
        [Element/model]
            ComposerViewComponent
        [web.Element/style]
            [web.scss/display]
                flex
            [web.scss/align-items]
                stretch
            [web.scss/align-self]
                stretch
            [web.scss/flex]
                0
                0
                auto
            [web.scss/min-height]
                41px
                {Dev/comment}
                    match minimal-height of input, including border width
            {if}
                @record
                .{ComposerViewComponent/isCompact}
                .{isFalsy}
            .{then}
                [web.scss/border]
                    0
                [web.scss/height]
                    auto
                [web.scss/padding]
                    0
                    10px
                [web.scss/width]
                    100%
            [web.scss/border]
                0
            {if}
                @record
                .{ComposerViewComponent/composerView}
                .{ComposerView/messageViewInEditing}
            .{then}
                [web.scss/border-right]
                    {scss/$border-width}
                    solid
                    {scss/$border-color}
`;
