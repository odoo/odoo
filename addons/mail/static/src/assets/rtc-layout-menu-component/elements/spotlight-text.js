/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            spotlightText
        [Element/model]
            RtcLayoutMenuComponent
        [Record/models]
            RtcLayoutMenuComponent/text
        [web.Element/textContent]
            {Locale/text}
                Spotlight
`;
