/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        States whether the current environment is QUnit test. Useful to
        disable some features that are not possible to test due to
        technical limitations.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            isQUnitTest
        [Field/model]
            Env
        [Field/type]
            attr
        [Field/target]
            Boolean
        [Field/default]
            false
`;
