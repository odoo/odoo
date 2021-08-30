/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Determines the last cursor start of the last composer related to this
        thread. Useful to sync the composer when re-creating it.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            textInputCursorStartBackup
        [Field/model]
            Thread
        [Field/type]
            attr
        [Field/target]
            Integer
        [Field/default]
            0
`;
