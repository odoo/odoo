/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            loadingMoreLabel
        [Element/model]
            MessageListComponent
        [web.Element/tag]
            span
        [web.Element/textContent]
            {Locale/text}
                Loading...
`;
