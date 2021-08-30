/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            root
        [Element/model]
            ChatterTopbarComponent
        [web.Element/style]
            [web.scss/display]
                flex
            [web.scss/flex-direction]
                row
            [web.scss/justify-content]
                space-between
            {Dev/comment}
                We need the +1 to handle the status bar border-bottom.
                The var is called $o-statusbar-height, but is used on button, therefore
                doesn't include the border-bottom.
                We use min-height to allow multiples buttons lines on mobile.
            [web.scss/min-height]
                {scss/$o-statusbar-height}
                .{+}
                    1
`;
