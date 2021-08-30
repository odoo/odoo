/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            removeButtonIcon
        [Element/model]
            FollowerComponent
        [web.Element/tag]
            i
        [web.Element/class]
            fa
            fa-remove
`;
