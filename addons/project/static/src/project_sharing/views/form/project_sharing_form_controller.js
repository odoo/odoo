/** @odoo-module */

import { _t } from "@web/core/l10n/translation";
import { FormController } from '@web/views/form/form_controller';
import { useService } from '@web/core/utils/hooks';
import { useExternalListener } from "@odoo/owl";

export class ProjectSharingFormController extends FormController {
    static components = {
        ...FormController.components,
    };

    setup() {
        super.setup();
        this.notification = useService('notification');
        useExternalListener(window, "paste", this.onGlobalPaste, { capture: true });
        useExternalListener(window, "drop", this.onGlobalDrop, { capture: true });
    }

    get actionMenuItems() {
        return {};
    }

    get translateAlert() {
        return null;
    }

    onGlobalPaste(ev) {
        if (ev.target.closest('.o_field_widget[name="description"]')) {
            ev.preventDefault();
            const items = ev.clipboardData.items;
            for (let i = 0; i < items.length; i++) {
                if (items[i].type.indexOf('image') !== -1 && !this.model.root.resId) {
                    this.notification.add(
                        _t("Save the task to be able to paste images in description"),
                        { type: 'warning' },
                    )
                    ev.stopImmediatePropagation();
                    return;
                }
            }
        }
    }

    onGlobalDrop(ev) {
        if (ev.target.closest('.o_field_widget[name="description"]')) {
            ev.preventDefault();
            if(ev.dataTransfer.files.length > 0 && !this.model.root.resId){
                this.notification.add(
                    _t("Save the task to be able to drag images in description"),
                    { type: 'warning' },
                )
                ev.stopImmediatePropagation();
            }
        }
    }
}
