/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Determine whether the drop zone should be visible or not.
        Note that this is an observed value, and primitive types such as
        boolean cannot be observed, hence this is an object with boolean
        value accessible from '.value'
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            value
        [Field/model]
            DropzoneVisibleComponentHook
        [Field/type]
            attr
        [Field/target]
            Boolean
        [Field/default]
            false
`;
