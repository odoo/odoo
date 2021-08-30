/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            spinnerLabel
        [Element/model]
            DiscussContainerComponent
        [web.Element/tag]
            span
        [web.Element/textContent]
            {Locale/text}
                Please wait...
`;
