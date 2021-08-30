/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            inviteButtonIcon
        [Element/model]
            ThreadViewTopbarComponent
        [web.Element/tag]
            i
        [web.Element/class]
            fa
            fa-lg
            fa-user-plus
`;