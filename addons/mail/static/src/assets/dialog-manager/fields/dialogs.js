/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        FIXME: dependent on implementation that uses insert order in relations!!
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            dialogs
        [Field/model]
            DialogManager
        [Field/type]
            many
        [Field/target]
            Dialog
        [Field/inverse]
            Dialog/manager
        [Field/isCausal]
            true
`;
