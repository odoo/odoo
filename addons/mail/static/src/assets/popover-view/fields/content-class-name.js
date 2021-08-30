/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Determines the class name for the component
        that is content of this popover view.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            contentClassName
        [Field/model]
            PopoverView
        [Field/type]
            attr
        [Field/target]
            String
        [Field/default]
            {String/empty}
`;
