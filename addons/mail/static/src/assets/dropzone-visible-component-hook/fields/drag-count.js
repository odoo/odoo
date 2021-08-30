/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Counts how many drag enter/leave happened globally. This is the only
        way to know if a file has been dragged out of the browser window.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            dragCount
        [Field/model]
            DropzoneVisibleComponentHook
        [Field/type]
            attr
        [Field/target]
            Number
        [Field/default]
            0
`;
