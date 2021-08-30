/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            noChatterLabel
        [Element/model]
            ChatterContainerComponent
        [web.Element/tag]
            span
        [web.Element/textContent]
            {Locale/text}
                Please wait...
`;
