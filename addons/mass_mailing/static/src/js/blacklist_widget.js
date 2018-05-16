odoo.define('mail.mass_mailing.blacklist.fields', function (require) {
    "use strict";
    var basicFields = require('web.basic_fields');
    var fieldRegistry = require('web.field_registry');

    var core = require('web.core');
    var qweb = core.qweb;

    var blacklist_widget = basicFields.FieldBoolean.extend({
            className: 'o_field_blacklisted_boolean',
            events: {
                'click': '_onClick',
            },
            init: function () {
                this._super.apply(this, arguments);
                this.blacklistedColor = 'red';
                this.whitelistColor = 'green';
            },
            /**
            * @override
            * @private
            */
            _render: function() {
                if (this.recordData.blacklist_reason != undefined && this.recordData.blacklist_reason) {
                    var no_html_reason = $( $.parseHTML(this.recordData.blacklist_reason) ).text();
                    this.$el.html($('<div title="' + no_html_reason + '">').css({
                        backgroundColor: this.value ? this.blacklistedColor : this.whitelistColor
                    }));
                }
                else
                {
                    this.$el.html($('<div>').css({
                        backgroundColor: this.value ? this.blacklistedColor : this.whitelistColor
                    }));
                }
            },
            _onClick: function() {
                if (this.viewType == 'form'){
                    return this._rpc({
                            model: this.model,
                            method: 'toggle_blacklist',
                            args: [this.res_id],
                        })
                        .then(function (ret) {
                              if (ret != 'not_found') {
                                  var color = ret ? 'red' : 'green'
                                  $('[name="is_blacklisted"]').html($('<div>').css({backgroundColor : color}))
                              }
                        });
                }
            },
        });

    fieldRegistry.add('blacklist_widget', blacklist_widget);
});