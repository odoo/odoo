odoo.define('website.backend.button', function (require) {
'use strict';

var AbstractField = require('web.AbstractField');
var core = require('web.core');
var field_registry = require('web.field_registry');

var _t = core._t;

var WebsitePublishButton = AbstractField.extend({
    className: 'o_stat_info',
    supportedFieldTypes: ['boolean'],

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * A boolean field is always set since false is a valid value.
     *
     * @override
     */
    isSet: function () {
        return true;
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * This widget is supposed to be used inside a stat button and, as such, is
     * rendered the same way in edit and readonly mode.
     *
     * @override
     * @private
     */
    _render: function () {
        this.$el.empty();
        var text = this.value ? _t("Published") : _t("Unpublished");
        var hover = this.value ? _t("Unpublish") : _t("Publish");
        var valColor = this.value ? 'text-success' : 'text-danger';
        var hoverColor = this.value ? 'text-danger' : 'text-success';
        var $val = $('<span>').addClass('o_stat_text o_not_hover ' + valColor).text(text);
        var $hover = $('<span>').addClass('o_stat_text o_hover ' + hoverColor).text(hover);
        this.$el.append($val).append($hover);
    },
});

var WidgetWebsiteButtonIcon = AbstractField.extend({
    template: 'WidgetWebsiteButtonIcon',
    events: {
        'click': '_onClick',
    },

    /**
    * @override
    */
    start: function () {
        this.$icon = this.$('.o_button_icon');
        return this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    isSet: function () {
        return true;
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _render: function () {
        this._super.apply(this, arguments);

        var published = this.value;
        var info = published ? _t("Published") : _t("Unpublished");
        this.$el.attr('aria-label', info)
                .prop('title', info);
        this.$icon.toggleClass('text-danger', !published)
                .toggleClass('text-success', published);
    },

    //--------------------------------------------------------------------------
    // Handler
    //--------------------------------------------------------------------------

    /**
     * Redirects to the website page of the record.
     *
     * @private
     */
    _onClick: function () {
        this.trigger_up('button_clicked', {
            attrs: {
                type: 'object',
                name: 'open_website_url',
            },
            record: this.record,
        });
    },
});

field_registry
    .add('website_redirect_button', WidgetWebsiteButtonIcon)
    .add('website_publish_button', WebsitePublishButton);
});
