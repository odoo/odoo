/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        States the OWL component of this popover view.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            component
        [Field/model]
            PopoverView
        [Field/type]
            attr
        [Field/target]
            PopoverViewComponent
        [Field/inverse]
            PopoverViewComponent/popoverView
`;
