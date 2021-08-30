/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Determines whether animations should be disabled.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            disableAnimation
        [Field/model]
            Env
        [Field/type]
            attr
        [Field/target]
            Boolean
        [Field/default]
            false
`;
