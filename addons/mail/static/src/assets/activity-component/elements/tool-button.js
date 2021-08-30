/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            toolButton
        [Element/model]
            ActivityComponent
        [Record/models]
            Hoverable
`;
