/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            fullscreenIcon
        [Element/model]
            RtcOptionListComponent
        [Record/models]
            RtcOptionListComponent/icon
        [web.Element/class]
            fa-arrows-alt
`;
