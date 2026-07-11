import { patch } from '@web/core/utils/patch';

import { SelectCreateDialog } from '@web/views/view_dialogs/select_create_dialog';

/** Toggle the select-create dialog between fullscreen and its initial size. */
patch(SelectCreateDialog.prototype, {
    onClickDialogSizeToggle() {
        this.env.dialogData.size =
            this.env.dialogData.size === 'fs' ? this.env.dialogData.initalSize : 'fs';
    },
});
