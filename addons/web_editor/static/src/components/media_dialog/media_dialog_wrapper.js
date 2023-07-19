
/** @odoo-module **/

import { useWowlService } from '@web/legacy/utils';
import { Component, onRendered, xml } from "@odoo/owl";
import { MediaDialog } from "./media_dialog";

export class MediaDialogWrapper extends Component {
    setup() {
        this.dialogs = useWowlService('dialog');

        onRendered(() => {
            this.dialogs.add(MediaDialog, this.props, {
                onClose: this.props.close,
            });
        });
    }
}
MediaDialogWrapper.template = xml``;
