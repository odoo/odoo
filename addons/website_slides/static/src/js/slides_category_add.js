/** @odoo-module **/

import publicWidget from 'web.public.widget';
import Dialog from 'web.Dialog';
import { _t } from 'web.core';

var CategoryAddDialog = Dialog.extend({
    template: 'slides.category.add',
    events: Object.assign(
        { "submit form#slide_category_add_form": "_onClickFormSubmit" },
        Dialog.events
    ),

    /**
     * @override
     */
    init: function (parent, options) {
        options = _.defaults(options || {}, {
            title: _t('Add a section'),
            size: 'medium',
            buttons: [{
                text: _t('Save'),
                classes: 'btn-primary o_js_website_slides_add_category_btn',
                click: this._onClickFormSubmit.bind(this),
            }, {
                text: _t('Back'),
                close: true
            }]
        });

        this.channelId = options.channelId;
        this._super(parent, options);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    _formValidate: function ($form) {
        $form.addClass('was-validated');
        return $form[0].checkValidity();
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Handle form submission on click button or press ENTER key. Prevent multiple submissions
     * @private
     * @param {Event} ev
     */
    _onClickFormSubmit: function (ev) {
        ev.preventDefault();
        const form = document.getElementById("slide_category_add_form");
        if (!form.classList.contains("o_js_website_slides_form_submitted")) {
            if (this._formValidate($(form))) {
                form.classList.add("o_js_website_slides_form_submitted");
                document.querySelector("button.o_js_website_slides_add_category_btn").disabled = true;
                form.submit();
            }
        }
    },
});

publicWidget.registry.websiteSlidesCategoryAdd = publicWidget.Widget.extend({
    selector: '.o_wslides_js_slide_section_add',
    events: {
        'click': '_onAddSectionClick',
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    _openDialog: function (channelId) {
        new CategoryAddDialog(this, {channelId: channelId}).open();
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
    categoryAddDialog: CategoryAddDialog,
    websiteSlidesCategoryAdd: publicWidget.registry.websiteSlidesCategoryAdd
};
