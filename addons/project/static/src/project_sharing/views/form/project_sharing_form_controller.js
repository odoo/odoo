/** @odoo-module */

import { FormController } from '@web/views/form/form_controller';

export class ProjectSharingFormController extends FormController {
    static components = {
        ...FormController.components,
    };

    get actionMenuItems() {
        return {};
    }

    get translateAlert() {
        return null;
    }
}
