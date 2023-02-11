odoo.define('pad.pad', function (require) {
"use strict";

var AbstractField = require('web.AbstractField');
var core = require('web.core');
var fieldRegistry = require('web.field_registry');

var _t = core._t;

var FieldPad = AbstractField.extend({
    template: 'FieldPad',
    content: "",
    events: _.extend({}, AbstractField.prototype.events, {
        'click .oe_pad_switch': '_onToggleFullScreen',
    }),
    isQuickEditable: true,
    quickEditExclusion: [
        '[href]',
    ],

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
        return this._super.apply(this, arguments);
    },
    /**
     * @override
     */
    start: function () {
        if (!this.isPadConfigured) {
            this.$(".oe_unconfigured").removeClass('d-none');
            this.$(".oe_configured").addClass('d-none');
            return Promise.resolve();
        }
        if (this.mode === 'edit' && typeof(this.value) === 'object') {
            this.value = this.value.toJSON();
        }
        if (this.mode === 'edit' && _.str.startsWith(this.value, 'http')) {
            this.url = this.value;
            // please close your eyes and look elsewhere...
            // Since the pad value (the url) will not change during the edition
            // process, we have a problem: the description field will not be
            // properly updated.  We need to explicitely write the value each
            // time someone edit the record in order to force the server to read
            // the updated value of the pad and put it in the description field.
            //
            // However, the basic model optimizes away the changes if they are
            // not really different from the current value. So, we need to
            // either add special configuration options to the basic model, or
            // to trick him into accepting the same value as being different...
            // Guess what we decided...
            var url = {};
            url.toJSON = _.constant(this.url);
            this._setValue(url, {doNotSetDirty: true});
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
        if (this.url) {
            // here, we have a valid url, so we can simply display an iframe
            // with the correct src attribute
            var userName = encodeURIComponent(this.getSession().name);
            var url = this.url + '?showChat=false&userName=' + userName;
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
                    object_id: this.res_id,
                    record: this.recordData,
                },
            }, {
                shadow: true
            }).then(function (result) {
                // We need to write the url of the pad to trigger
                // the write function which updates the actual value
                // of the field to the value of the pad content
                self.url = result.url;
                self._setValue(result.url, {doNotSetDirty: true});
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
                _.each(self.$('a'), (link) => {
                    if (link.hostname !== window.location.hostname && link.target === "") {
                        link.target = "_blank";
                    }
                });
            }).guardedCatch(function () {
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
    _onKeydown: function () {
        // managed by the pad.
    },
    /**
     * @override
     * @private
     */
    _onToggleFullScreen: function () {
        this.$el.toggleClass('oe_pad_fullscreen mb0');
        this.$('.oe_pad_switch').toggleClass('fa-expand fa-compress');
        this.$el.parents('.o_touch_device').toggleClass('o_scroll_hidden');
    },
});

fieldRegistry.add('pad', FieldPad);

return FieldPad;

});
