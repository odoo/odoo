odoo.define('website_slides.add.section', function (require) {
'use strict';

var sAnimations = require('website.content.snippets.animation');
var Dialog = require('web.Dialog');
var core = require('web.core');
var _t = core._t;

var SectionDialog = Dialog.extend({
    template: 'website.slide.add.section',

    /**
     * @override
     */
    init: function (parent, options) {
        options = _.defaults(options || {}, {
            title: _t("Add a section"),
            size: 'medium',
            buttons: [{
                text: _t("Save"),
                classes: 'btn-primary',
                click: this._onClickFormSubmit.bind(this)
            }, {
                text: _t("Discard"),
                close: true
            }]
        });

        this.channelId = options.channelId;
        this._super(parent, options);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    _onClickFormSubmit: function (ev) {
        var $form = this.$("#slide_category_add_form");
        if (this._formValidate($form)) {
            $form.submit();
        }
    },

    _formValidate: function ($form) {
        $form.addClass('was-validated');
        return $form[0].checkValidity();
    },
});

sAnimations.registry.websiteSlidesSection = sAnimations.Class.extend({
    selector: '.oe_slide_js_add_section',
    xmlDependencies: ['/website_slides/static/src/xml/website_slides_upload.xml'],
    read_events: {
        'click': '_onAddSectionClick',
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    _openDialog: function (channelId) {
        new SectionDialog(this, {channelId: channelId}).open();
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

return {
    sectionDialog: SectionDialog,
    websiteSlidesSection: sAnimations.registry.websiteSlidesSection
};

});
