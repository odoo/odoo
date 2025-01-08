import { _t } from "@web/core/l10n/translation";
import publicWidget from '@web/legacy/js/public/public_widget';
import { CategoryAddDialog } from "@website_slides/js/public/components/category_add_dialog/category_add_dialog";

publicWidget.registry.websiteSlidesCategoryAdd = publicWidget.Widget.extend({
    selector: '.o_wslides_js_slide_section_add',
    events: {
        'click': '_onAddSectionClick',
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    _openDialog: function (channelId) {
        this.call("dialog", "add", CategoryAddDialog, {
            title: _t("Add a section"),
            confirmLabel: _t("Save"),
            confirm: ({ formEl }) => {
                if (!formEl.checkValidity()) {
                    return false;
                }
                formEl.classList.add("was-validated");
                formEl.submit();
                return true;
            },
            cancelLabel: _t("Back"),
            cancel: () => {},
            channelId,
        });
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {Event} ev
     */
    _onAddSectionClick: function (ev) {
        ev.preventDefault();
        this._openDialog($(ev.currentTarget).attr('channel_id'));
    },
});

export default {
    websiteSlidesCategoryAdd: publicWidget.registry.websiteSlidesCategoryAdd
};
