/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            exitFullscreenLabel
        [Element/model]
            RtcOptionListComponent
        [Record/models]
            RtcOptionListComponent/label
        [web.Element/textContent]
            {Locale/text}
                Exit full screen
`;
