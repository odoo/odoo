/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            actionButtons
        [Element/model]
            ComposerViewComponent
        [web.Element/style]
            {if}
                @record
                .{ComposerViewComponent/isCompact}
            .{then}
                [web.scss/display]
                    flex
            {if}
                @record
                .{ComposerViewComponent/isCompact}
                .{isFalsy}
            .{then}
                [web.scss/margin-top]
                    {scss/map-get}
                        {scss/$spacers}
                        2
`;
