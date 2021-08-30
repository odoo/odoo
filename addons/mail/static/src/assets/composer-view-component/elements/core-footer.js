/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            coreFooter
        [Element/model]
            ComposerViewComponent
        [Element/isPresent]
            @record
            .{ComposerViewComponent/hasFooter}
        [web.Element/style]
            [web.scss/grid-area]
                core-footer
            [web.scss/overflow-x]
                hidden
            {if}
                @record
                .{ComposerViewComponent/isCompact}
                .{isFalsy}
            .{then}
                [web.scss/margin-left]
                    0
`;
