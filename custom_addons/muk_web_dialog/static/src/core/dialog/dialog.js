import { session } from '@web/session';
import { patch } from '@web/core/utils/patch';

import { Dialog } from '@web/core/dialog/dialog';

/** Honor the user dialog size preference and add a fullscreen size toggle. */
patch(Dialog.prototype, {
    setup() {
        super.setup();
        this.data.size = session.dialog_size !== 'maximize' ? this.props.size : 'fs';
        this.data.initalSize = this.props?.size || 'lg';
    },
    onClickDialogSizeToggle() {
        this.data.size = this.data.size === 'fs' ? this.data.initalSize : 'fs';
    },
});
