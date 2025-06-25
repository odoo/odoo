/** @odoo-module **/

import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import publicWidget from "@web/legacy/js/public/public_widget";
import { _t } from "@web/core/l10n/translation";

publicWidget.registry.websiteSlidesCategoryDelete = publicWidget.Widget.extend({
    selector: ".o_wslides_js_category_delete",
    events: {
        click: "_onClickDeleteCateogry",
    },

    init() {
        this._super(...arguments);
        this.orm = this.bindService("orm");
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickDeleteCateogry(ev) {
        const categoryId = parseInt(ev.currentTarget.dataset.categoryId);
        this.call("dialog", "add", ConfirmationDialog, {
            title: _t("Delete Category"),
            body: _t("Are you sure you want to delete this category?"),
            confirmLabel: _t("Delete"),
            confirm: async () => {
                /**
                 * Calls 'unlink' method on slides.slide to delete the category and
                 * reloads page after deletion to re-arrange the content on UI
                 */
                await this.orm.unlink("slide.slide", [categoryId]);
                window.location.reload();
            },
            cancel: () => {},
        });
    },
});

export default {
    websiteSlidesCategoryDelete: publicWidget.registry.websiteSlidesCategoryDelete,
};
