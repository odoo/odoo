/** @odoo-module **/

import { Define } from '@mail/define';


export default Define`
    {Dev/comment}
        class FormViewDialogComponentAdapter extends ComponentAdapter {

            renderWidget() {
                // Ensure the dialog is properly reconstructed. Without this line, it is
                // impossible to open the dialog again after having it closed a first
                // time, because the DOM of the dialog has disappeared.
                return this.willStart();
            }

        }
    {Record/insert}
        [Record/models]
            Model
        [Model/name]
            ComposerSuggestedRecipientComponent
        [Model/components]
            FormViewDialogComponentAdapter
        [Model/fields]
            _dialogWidget
            _isDialogOpen
            id
            suggestedRecipientInfo
        [Model/template]
            root
                checkbox
                    checkboxInput
                    checkboxLabel
                formViewDialog
        [Model/lifecycles]
            onUpdate
`;
