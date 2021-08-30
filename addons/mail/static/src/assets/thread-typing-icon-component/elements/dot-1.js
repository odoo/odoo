/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            dot1
        [Element/model]
            ThreadTypingIconComponent
        [web.Element/tag]
            span
        [Record/models]
            ThreadTypingIconComponent/dot
`;
