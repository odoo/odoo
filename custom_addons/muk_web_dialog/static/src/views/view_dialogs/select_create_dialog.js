import { patch } from '@web/core/utils/patch';

import { SelectCreateDialog } from '@web/views/view_dialogs/select_create_dialog';

patch(SelectCreateDialog.prototype, {
    onClickDialogSizeToggle() {
        this.env.dialogData.size = (
            this.env.dialogData.size === 'fs' ? this.env.dialogData.initalSize : 'fs'
        );
    }
});