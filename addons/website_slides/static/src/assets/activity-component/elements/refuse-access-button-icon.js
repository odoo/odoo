/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            refuseAccessButtonIcon
        [Element/feature]
            website_slides
        [Element/model]
            ActivityComponent
        [web.Element/tag]
            i
        [web.Element/class]
            fa
            fa-times
`;
