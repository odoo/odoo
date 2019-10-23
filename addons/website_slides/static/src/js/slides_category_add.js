odoo.define('website_slides.category.add', function (require) {
'use strict';

var publicWidget = require('web.public.widget');
var Dialog = require('web.Dialog');
var core = require('web.core');
var _t = core._t;

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
        this.modulesToInstall = options.modulesToInstall;
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
        var self = this;
        if (this._formValidate($form)) {
            this._rpc({
                route : '/slides/category/add',
                params: {
                    channel_id: self.channelId,
                    name: $form[0].name.value
                }
            }).then(function (data) {
                if (!data.error) {
                    data.modulesToInstallString = self.modulesToInstall;
                    data.onSuccess = self.close.bind(self);
                    self.trigger_up('append_new_content', data);
                }
            });
        }
    },
});

publicWidget.registry.websiteSlidesCategoryAdd = publicWidget.Widget.extend({
    xmlDependencies: ['/website_slides/static/src/xml/slide_management.xml'],
    events: {
        'click': '_onAddSectionClick',
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    _openDialog: function () {
        new CategoryAddDialog(this, {channelId: this.channelId, modulesToInstall: this.modulesToInstall}).open();
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
        this.channelId = $(ev.currentTarget).data('channelId'),
        this.modulesToInstall = $(ev.currentTarget).data('modulesToInstall');
        this._openDialog();
    },
});

return {
    categoryAddDialog: CategoryAddDialog,
    websiteSlidesCategoryAdd: publicWidget.registry.websiteSlidesCategoryAdd
};

});
