/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            root
        [Element/model]
            ThreadTypingIconComponent
        [web.Element/title]
            @record
            .{ThreadTypingIconComponent/title}
        [web.Element/style]
            [web.scss/display]
                flex
            [web.scss/align-items]
                center
`;
