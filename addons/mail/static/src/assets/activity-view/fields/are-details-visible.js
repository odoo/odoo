/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Determines whether the details are visible.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            areDetailsVisible
        [Field/model]
            ActivityView
        [Field/type]
            attr
        [Field/target]
            Boolean
        [Field/default]
            false
`;
