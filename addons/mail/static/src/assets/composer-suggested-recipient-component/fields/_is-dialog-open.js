/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Whether the dialog is currently open. 'dialog' element cannot be trusted
        to know if the dialog is open due to manually calling 'open' and
        potential out of sync with component adapter.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            _isDialogOpen
        [Field/model]
            ComposerSuggestedRecipientComponent
        [Field/type]
            attr
        [Field/target]
            Boolean
        [Field/default]
            false
`;
