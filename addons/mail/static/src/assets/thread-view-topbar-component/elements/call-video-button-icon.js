/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            callVideoButtonIcon
        [Element/model]
            ThreadViewTopbarComponent
        [web.Element/tag]
            i
        [web.Element/class]
            fa
            fa-lg
            fa-camera
`;
