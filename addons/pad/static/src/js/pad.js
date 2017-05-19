odoo.define('pad.pad', function (require) {
"use strict";

var AbstractField = require('web.AbstractField');
var core = require('web.core');
var fieldRegistry = require('web.field_registry');

var _t = core._t;

var FieldPad = AbstractField.extend({
    template: 'FieldPad',
    content: "",
    events: {
        'click .oe_pad_switch': '_onToggleFullScreen',
    },
    supportedFieldTypes: ['char'],

    /**
     * @override
     */
    willStart: function () {
        if (this.isPadConfigured === undefined) {
            return this._rpc({
                method: 'pad_is_configured',
                model: this.model,
            }).then(function (result) {
                // we write on the prototype to share the information between
                // all pad widgets instances, across all actions
                FieldPad.prototype.isPadConfigured = result;
            });
        }
        return $.when();
    },
    /**
     * @override
     */
    start: function () {
        if (!this.isPadConfigured) {
            this.$(".oe_unconfigured").removeClass('hidden');
            this.$(".oe_configured").addClass('hidden');
            return;
        }
        return this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * If we had to generate an url, we wait for the generation to be completed,
     * so the current record will be associated with the correct pad url.
     *
     * @override
     */
    commitChanges: function () {
        return this.urlDef;
    },
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
     * Note that this method has some serious side effects: performing rpcs and
     * setting the value of this field.  This is not conventional and should not
     * be copied in other code, unless really necessary.
     *
     * @override
     * @private
     */
    _renderEdit: function () {
        if (_.str.startsWith(this.value, 'http')) {
            // here, we have a valid url, so we can simply display an iframe
            // with the correct src attribute
            var userName = encodeURIComponent(this.getSession().userName);
            var url = this.value + '?showChat=false&userName=' + userName;
            var content = '<iframe width="100%" height="100%" frameborder="0" src="' + url + '"></iframe>';
            this.$('.oe_pad_content').html(content);
        } else if (this.value) {
            // it looks like the field does not contain a valid url, so we just
            // display it (it cannot be edited in that case)
            this.$('.oe_pad_content').text(this.value);
        } else {
            // It is totally discouraged to have a render method that does
            // non-rendering work, especially since the work in question
            // involves doing RPCs and changing the value of the field.
            // However, this is kind of necessary in this case, because the
            // value of the field is actually only the url of the pad. The
            // actual content will be loaded in an iframe.  We could do this
            // work in the basic model, but the basic model does not know that
            // this widget is in edit or readonly, and we really do not want to
            // create a pad url everytime a task without a pad is viewed.
            var self = this;
            this.urlDef = this._rpc({
                method: 'pad_generate_url',
                model: this.model,
                context: {
                    model: this.model,
                    field_name: this.name,
                    object_id: this.res_id
                },
            }, {
                shadow: true
            }).then(function (result) {
                // We need to write the url of the pad to trigger
                // the write function which updates the actual value
                // of the field to the value of the pad content
                self._setValue(result.url);
            });
        }
    },
    /**
     * @override
     * @private
     */
    _renderReadonly: function () {
        if (_.str.startsWith(this.value, 'http')) {
            var self = this;
            this.$('.oe_pad_content')
                .addClass('oe_pad_loading')
                .text(_t("Loading"));
            this._rpc({
                method: 'pad_get_content',
                model: this.model,
                args: [this.value]
            }, {
                shadow: true
            }).then(function (data) {
                self.$('.oe_pad_content')
                    .removeClass('oe_pad_loading')
                    .html('<div class="oe_pad_readonly"><div>');
                self.$('.oe_pad_readonly').html(data);
            }).fail(function () {
                self.$('.oe_pad_content').text(_t('Unable to load pad'));
            });
        } else {
            this.$('.oe_pad_content')
                .addClass('oe_pad_loading')
                .show()
                .text(_t("This pad will be initialized on first edit"));
        }
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @override
     * @private
     */
    _onToggleFullScreen: function () {
        this.$el.toggleClass('oe_pad_fullscreen mb0');
        this.$('.oe_pad_switch').toggleClass('fa-expand fa-compress');
    },
});

fieldRegistry.add('pad', FieldPad);

return FieldPad;

});
