odoo.define('pad.pad', function (require) {

var core = require('web.core');
var form_common = require('web.form_common');

var _t = core._t;

var FieldPad = form_common.AbstractField.extend(form_common.ReinitializeWidgetMixin, {
    template: 'FieldPad',
    content: "",
    init: function() {
        var self = this;
        this._super.apply(this, arguments);
        this._configured_deferred = this.view.dataset.call('pad_is_configured').then(function(data) {
            self.set("configured", !!data);
        }).fail(function(data, event) {
            event.preventDefault();
            self.set("configured", true);
        });
        // CHANGES ONLY NEEDED UNTIL SAAS-15
        // deferred for request getting pad content (readonly) or new pad url (edit)
        this._pad_loading_deferred = null;
    },
    initialize_content: function() {
        var self = this;
        this.$('.oe_pad_switch').click(function() {
            self.$el.toggleClass('oe_pad_fullscreen');
            self.$el.find('.oe_pad_switch').toggleClass('fa-expand fa-compress');
            self.view.$el.find('.oe_chatter').toggle();
            $('#oe_main_menu_navbar').toggle();
        });
        this._configured_deferred.always(function() {
            var configured = self.get('configured');
            self.$(".oe_unconfigured").toggle(!configured);
            self.$(".oe_configured").toggle(configured);
        });
        this.render_value();
    },
    render_value: function() {
        var self = this;
        $.when(this._configured_deferred).always(function() {
            if (!self.get('configured')){
                return;
            }

            // reject previously ongoing _pad_loading_deferred
            if (self._pad_loading_deferred !== null) {
                self._pad_loading_deferred.reject();
                self.$('.oe_pad_content').removeClass('oe_pad_loading').html('');
            }
            self._pad_loading_deferred = $.Deferred();
            // keep reference to current _pad_loading_deferred
            var loading_def = self._pad_loading_deferred;

            var value = self.get('value');
            if (self.get('effective_readonly')) {
                if (_.str.startsWith(value, 'http')) {
                    self.view.dataset.call('pad_get_content', {url: value}).then(loading_def.resolve, loading_def.reject);
                    loading_def.done(function(data) {
                        self.$('.oe_pad_content').removeClass('oe_pad_loading').html('<div class="oe_pad_readonly"><div>');
                        self.$('.oe_pad_readonly').html(data);
                    }).fail(function() {
                        self.$('.oe_pad_content').text(_t('Unable to load pad'));
                    });
                } else {
                    self.$('.oe_pad_content').addClass('oe_pad_loading').show().text(_t("This pad will be initialized on first edit"));
                }
            }
            else {
                var def = $.Deferred();
                if (! value || !_.str.startsWith(value, 'http')) {
                    var deferreds = [
                        self.view.dataset.call('pad_generate_url', {
                            context: {
                                model: self.view.model,
                                field_name: self.name,
                                object_id: self.view.datarecord.id
                            }
                        }),
                        // change record only after record_loaded and its call stack is finished
                        self.view.record_loaded.then(function() {
                            var call_stack_ended = $.Deferred();
                            _.defer(call_stack_ended.resolve);
                            return call_stack_ended;
                        })
                    ];
                    // delay onchange after x2many views are loaded
                    deferreds = deferreds.concat(_.compact(_.pluck(self.view.fields, 'is_loaded')));
                    $.when.apply($, deferreds).then(function(data) {
                        // update value only if loading_def has not been previously rejected
                        loading_def.resolve().done(function(){
                            if (! data.url) {
                                self.set("configured", false);
                            } else {
                                self.internal_set_value(data.url);
                            }
                        }).then(def.resolve, def.reject);
                    });
                } else {
                    def.resolve();
                }
                def.then(function() {
                    value = self.get('value');
                    if (_.str.startsWith(value, 'http')) {
                        var content = '<iframe width="100%" height="100%" frameborder="0" src="' + value + '?showChat=false&userName=' + encodeURIComponent(self.session.username) + '"></iframe>';
                        self.$('.oe_pad_content').html(content);
                        self._dirty_flag = true;
                    }
                    else {
                        self.$('.oe_pad_content').text(value);
                    }
                });
            }
        });
    },
    is_false: function() {
        return false;
    }
});

core.form_widget_registry.add('pad', FieldPad);

});