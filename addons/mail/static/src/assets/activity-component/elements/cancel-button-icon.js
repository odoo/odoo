/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            cancelButtonIcon
        [Element/model]
            ActivityComponent
        [web.Element/tag]
            i
        [web.Element/class]
            fa
            fa-times
`;
