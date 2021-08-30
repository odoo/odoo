/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            button
        [Element/model]
            ComposerViewComponent
        [web.Element/style]
            {if}
                @record
                .{ComposerViewComponent/isCompact}
            .{then}
                [web.scss/border-left]
                    none
                    {Dev/comment}
                        overrides bootstrap button style
                {web.scss/selector}
                    [0]
                        :last-child
                    [1]
                        [web.scss/border-radius]
                            0
                            3px
                            3px
                            0
`;
