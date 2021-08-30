/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Determines the last content of the last composer related to this
        thread. Useful to sync the composer when re-creating it.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            textInputContentBackup
        [Field/model]
            Thread
        [Field/type]
            attr
        [Field/target]
            String
`;
