/** @odoo-module **/

import publicWidget from 'web.public.widget';
import Dialog from 'web.Dialog';
import { _t } from 'web.core';

var CategoryAddDialog = Dialog.extend({
    template: 'slides.category.add',

    /**
     * @override
     */
    init: function (parent, options) {
        options = _.defaults(options || {}, {
            title: _t('Add a section'),
            size: 'medium',
            buttons: [{
                text: _t('Save'),
                classes: 'btn-primary',
                click: this._onClickFormSubmit.bind(this)
            }, {
                text: _t('Discard'),
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

    _onClickFormSubmit: function (ev) {
        var $form = this.$('#slide_category_add_form');
        if (this._formValidate($form)) {
            $form.submit();
        }
    },
});

publicWidget.registry.websiteSlidesCategoryAdd = publicWidget.Widget.extend({
    selector: '.o_wslides_js_slide_section_add',
    xmlDependencies: ['/website_slides/static/src/xml/slide_management.xml'],
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
