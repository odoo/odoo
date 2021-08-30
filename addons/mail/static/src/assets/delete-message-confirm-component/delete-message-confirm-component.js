/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Model
        [Model/name]
            DeleteMessageConfirmComponent
        [Model/fields]
            deleteMessageConfirmView
        [Model/template]
            root
                title
                separator
                question
                blockquote
                attention
                separator
                buttons
                    deleteButton
                    cancelButton
`;
