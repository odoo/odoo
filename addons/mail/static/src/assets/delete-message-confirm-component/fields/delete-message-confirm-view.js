/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            deleteMessageConfirmView
        [Field/model]
            DeleteMessageConfirmDialogComponent
        [Field/type]
            one
        [Field/target]
            DeleteMessageConfirmView
        [Field/isRequired]
            true
        [Field/inverse]
            DeleteMessageConfirmView/component
`;
