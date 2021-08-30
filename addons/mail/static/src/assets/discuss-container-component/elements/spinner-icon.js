/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            spinnerIcon
        [Element/model]
            DiscussContainerComponent
        [web.Element/class]
            fa
            fa-circle-o-notch
            fa-spin
            me-2
`;
