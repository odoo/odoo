odoo.define('pad.pad', function (require) {
"use strict";

var AbstractField = require('web.AbstractField');
var core = require('web.core');
var field_registry = require('web.field_registry');

var _t = core._t;


var FieldPad = AbstractField.extend({
    template: 'FieldPad',
    content: "",
    events: {
        'click .oe_pad_switch': function() {
            this.$el.toggleClass('oe_pad_fullscreen mb0');
            this.$('.oe_pad_switch').toggleClass('fa-expand fa-compress');
        },
    },
    supportedFieldTypes: ['char'],
    init: function() {
        var self = this;
        this._super.apply(this, arguments);

        this.configured = false;
        this._configured_deferred = $.Deferred();
        this._url_request_deferred = $.Deferred();

        this.trigger_up('perform_model_rpc', {
            method: 'pad_is_configured',
            model: this.model,
            on_success: function (data) {
                self.set_configured(!!data);
                self._configured_deferred.resolve();
            },
            on_fail: function () {
                self.set_configured(true);
                self._configured_deferred.resolve();
            },
        });
    },
    render_readonly: function() {
        var self = this;
        this._configured_deferred.then(function() {
            if (self.configured){
                if (_.str.startsWith(self.value, 'http')) {
                        self.trigger_up('perform_model_rpc', {
                            method: 'pad_get_content',
                            model: self.model,
                            args: [self.value],
                            on_success: function(data) {
                                self.$('.oe_pad_content').removeClass('oe_pad_loading').html('<div class="oe_pad_readonly"><div>');
                                self.$('.oe_pad_readonly').html(data);
                            },
                            on_fail: function() {
                                self.$('.oe_pad_content').text(_t('Unable to load pad'));
                            }
                        });
                } else {
                    self.$('.oe_pad_content').addClass('oe_pad_loading').show().text(_t("This pad will be initialized on first edit"));
                }
            }
        });
    },
    render_edit: function() {
        var self = this;
        this._configured_deferred.then(function() {
            if (! self.value || !_.str.startsWith(self.value, 'http')) {
                self.trigger_up('perform_model_rpc', {
                    method: 'pad_generate_url',
                    model: self.model,
                    context: {
                        model: self.model,
                        field_name: self.name,
                        object_id: self.model
                    },
                    on_success: function(data) {
                        if (! data.url) {
                            self.set_configured(false);
                        } else {
                            self.set_value(data.url);
                        }
                        self._url_request_deferred.resolve();
                    },
                });
            } else {
                // We need to write the url of the pad to trigger
                // the write function which updates the actual value
                // of the field to the value of the pad content
                self.set_value(self.value);
                self._url_request_deferred.resolve();
            }
            self._url_request_deferred.then(function() {
                if (_.str.startsWith(self.value, 'http')) {
                    var content = '<iframe width="100%" height="100%" frameborder="0" src="' + self.value + '?showChat=false&userName=' + encodeURIComponent(self.session.username) + '"></iframe>';
                    self.$('.oe_pad_content').html(content);
                }
                else {
                    self.$('.oe_pad_content').text(self.value);
                }
            });
        });
    },
    set_configured: function(configured) {
        this.configured = configured;
        if (!configured) {
            this.$(".oe_unconfigured").removeClass('hidden');
            this.$(".oe_configured").addClass('hidden');
        }
    },
    is_set: function() {
        return true;
    },
});

field_registry.add('pad', FieldPad);

});
