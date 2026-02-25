import { Component, markup } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { PermissionPromptDialog } from "@web/core/permission_prompt_dialog/permission_prompt_dialog";

const SLIDERS_ICON_SVG = `<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M14 17H5"></path><path d="M19 7h-9"></path><circle cx="17" cy="17" r="3"></circle><circle cx="7" cy="7" r="3"></circle></svg>`;

export class NotificationAlertDialog extends Component {
    static components = { PermissionPromptDialog };
    static defaultProps = {
        animateMouse: true,
    };
    static props = ["animateMouse?", "close"];
    static template = "web.NotificationAlertDialog";

    get stepOneText() {
        return _t("Click the %(icon)s page info icon in your browser's address bar.", {
            icon: markup(SLIDERS_ICON_SVG),
        });
    }
}
