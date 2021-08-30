/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            root
        [Element/model]
            DiscussSidebarComponent
        [web.Element/style]
            [web.scss/display]
                flex
            [web.scss/flex-flow]
                column
            [web.scss/width]
                {scss/$o-mail-chat-sidebar-width}
            {web.scss/include}
                {web.scss/media-breakpoint-up}
                    [0]
                        xl
                    [1]
                        [web.scss/width]
                            {scss/$o-mail-chat-sidebar-width}
                            .{+}
                                50px
`;
