/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Inverse of the messaging field present on all models. This field
        therefore contains all existing records.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            allRecords
        [Field/model]
            Env
        [Field/type]
            many
        [Field/target]
            Record
        [Field/inverse]
            Record/env
        [Field/isCausal]
            true
`;
