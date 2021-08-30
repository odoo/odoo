/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            headerItemButtonIcon
        [Element/model]
            AttachmentViewerComponent
        [web.Element/style]
            {if}
                {Device/isSmall}
                .{isFalsy}
            .{then}
                [web.scss/margin-right]
                    {scss/map-get}
                        {scss/$spacers}
                        2
`;
