/** @odoo-module */

import { registry } from "@web/core/registry";
import { Dialog } from "@web/core/dialog/dialog";
import { _lt } from "@web/core/l10n/translation";
import { Component } from "@odoo/owl";

class ScssErrorDialog extends Component {}
ScssErrorDialog.template = "web.ScssErrorDialog";
ScssErrorDialog.components = { Dialog };
ScssErrorDialog.title = _lt("Style error");

const scssErrorDisplayService = {
    dependencies: ["dialog"],
    start(env, { dialog }) {
        if (window.__odooScssCompilationError) {
            dialog.add(ScssErrorDialog, {
                message: window.__odooScssCompilationError,
            });
        }
    },
};

registry.category("services").add("scss_error_display", scssErrorDisplayService);
