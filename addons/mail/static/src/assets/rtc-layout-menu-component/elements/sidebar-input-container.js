/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            sidebarInputContainer
        [Element/model]
            RtcLayoutMenuComponent
        [Record/models]
            RtcLayoutMenuComponent/inputContainer
`;
