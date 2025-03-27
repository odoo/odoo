import publicWidget from '@web/legacy/js/public/public_widget';

publicWidget.registry.WebsiteProfileSearchModal = publicWidget.Widget.extend({
    selector: '#o_wprofile_search_modal',
    disabledInEditableMode: true,

    //--------------------------------------------------------------------------
    // Overrides
    //--------------------------------------------------------------------------
    start() {
        this._super(...arguments);

        this.el.addEventListener("shown.bs.modal", (ev) => {
            ev.target.querySelector('.oe_search_box').focus();
        });
    },
});

export default {
    WebsiteProfileSearchModal: publicWidget.registry.WebsiteProfileSearchModal
};
