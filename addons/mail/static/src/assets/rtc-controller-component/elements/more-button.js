/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            moreButton
        [Element/model]
            RtcControllerComponent
        [Record/models]
            RtcControllerComponent/button
        [web.Element/aria-label]
            {Locale/text}
                More
        [web.Element/title]
            {Locale/text}
                More
`;
