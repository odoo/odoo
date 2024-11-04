import { _t } from "@web/core/l10n/translation";
import publicWidget from "@web/legacy/js/public/public_widget";

publicWidget.registry.RegisterToasterWidget = publicWidget.Widget.extend({
    selector: '.o_wevent_register_toaster',
    /**
     * @override
     */
    init() {
        this._super(...arguments);
        this.notification = this.bindService("notification");
    },
    /**
     * This widget allows to display a toast message on the page.
     *
     * @override
     */
    start: function () {
        const message = this.el.dataset.message;
        if (message && message.length) {
            this.notification.add(message, {
                title: _t("Register"),
                type: 'info',
            });
        }
        return this._super.apply(this, arguments);
    },
});

export default publicWidget.registry.RegisterToasterWidget;
