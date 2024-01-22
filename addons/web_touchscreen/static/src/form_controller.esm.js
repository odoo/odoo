/** @odoo-module **/
/* Copyright 2023 Moduon Team S.L.
 * License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0) */

import {FormController} from "@web/views/form/form_controller";
import {patch} from "@web/core/utils/patch";
import {hasTouch} from "@web/core/browser/feature_detection";

patch(FormController.prototype, "web_touchscreen.FormController", {
    setup() {
        const wasSmall = this.env.isSmall;
        // Create a new env that extends the original one but overrides the way
        // Odoo considers this device small: it will be small if it has touch
        // capabilities, not only if the screen is small. In practice, this
        // will make the inline subforms prefer the kanban mode if possible.
        const newEnv = {isSmall: wasSmall || hasTouch()};
        Object.setPrototypeOf(newEnv, this.env);
        this.env = newEnv;
        return this._super(...arguments);
    },
});
