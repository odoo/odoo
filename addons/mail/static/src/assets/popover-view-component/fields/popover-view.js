/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            popoverView
        [Field/model]
            PopoverViewComponent
        [Field/type]
            one
        [Field/target]
            PopoverView
        [Field/inverse]
            PopoverView/component
`;
