/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            primaryToolButtons
        [Element/model]
            ComposerViewComponent
        [web.Element/style]
            [web.scss/display]
                flex
            [web.scss/align-items]
                center
            {if}
                @record
                .{ComposerViewComponent/isCompact}
            .{then}
                [web.padding-left]
                    {scss/map-get}
                        {scss/$spacers}
                        2
                [web.scss/padding-right]
                    {scss/map-get}
                        {scss/$spacers}
                        2
`;
