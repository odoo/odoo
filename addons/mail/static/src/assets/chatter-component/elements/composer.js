/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            composer
        [Element/model]
            ChatterComponent
        [Field/target]
            ComposerViewComponent
        [Element/isPresent]
            @record
            .{ChatterComponent/chatter}
            .{Chatter/composerView}
        [ComposerViewComponent/composerView]
            @record
            .{ChatterComponent/chatter}
            .{Chatter/composerView}
        [ComposerViewComponent/hasFollowers]
            true
        [ComposerViewComponent/hasMentionSuggestionsBelowPosition]
            true
        [ComposerViewComponent/isCompact]
            false
        [ComposerViewComponent/isExpandable]
            true
        [web.Element/style]
            [web.scss/border-bottom]
                {scss/$border-width}
                solid
            [web.scss/border-bottom-color]
                {scss/$border-color}
            {if}
                @record
                .{ChatterComponent/chatter}
                .{Chatter/hasExternalBorder}
            .{then}
                [web.scss/border-left]
                    {scss/$border-width}
                    solid
                [web.scss/border-right]
                    {scss/$border-width}
                    solid
                [web.scss/border-left-color]
                    {scss/$border-color}
                [web.scss/border-right-color]
                    {scss/$border-color}
`;
