/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            titleEndLine
        [Element/model]
            ActivityBoxComponent
        [Record/models]
            ActivityBoxComponent/titleLine
        [web.Element/class]
            ms-3
`;
