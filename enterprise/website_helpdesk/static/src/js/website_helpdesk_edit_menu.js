/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { MenuDialog } from "@website/components/dialog/edit_menu";

/**
 * The goal of this patch is to prevent users from creating
 * website menu item with url of format /helpdesk/<team-slug> or /helpdesk
 */
patch(MenuDialog.prototype, {
    /**
     * @override
     */
    setup() {
        super.setup();
        this.notification = useService('notification');
        this.originalUrl = this.props.url;
    },
    /**
     * @override
     */
    onClickOk() {
        // do not prevent editing the menu item's name
        const hasUrlChanged = this.url.input.value !== this.originalUrl;
        if (hasUrlChanged && this.url.isValid()) {
            const isHelpdeskUrl = this.url.input.value === "/helpdesk";
            const isHelpdeskTeamPattern = isHelpdeskUrl || /^\/helpdesk\/([a-zA-Z]+-)+\d+$/.test(this.url.input.value);
            if (isHelpdeskUrl || isHelpdeskTeamPattern) {
                this.url.input.hasError = true;
                this.notification.add(
                    isHelpdeskUrl ?
                        _t("This URL is reserved for the helpdesk teams with 'website form' feature enabled.")
                        : _t("The %s URL is reserved for the helpdesk team with the same name. \
                        To use it, please enable the 'website form' feature on that team instead.", this.url.input.value),
                    { type: 'danger' },
                );
                return;
            }
        }
        super.onClickOk();
    },
});
