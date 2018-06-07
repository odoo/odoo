odoo.define('mail.mass_mailing.blacklist.fields', function (require) {
    "use strict";
    var basicFields = require('web.basic_fields');
    var fieldRegistry = require('web.field_registry');

    var core = require('web.core');
    var qweb = core.qweb;

    var blacklist_state = {};

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
                // If the widget is visible twice on the screen (ex in list + in wizard form)
                // The original value is not recomputed and kept in the cache so we have to store the value on client side
                var is_blacklisted = false;
                if (document.getElementsByClassName('toggle_blacklist_' + this.res_id).length > 1 && this.res_id in blacklist_state){
                    is_blacklisted = blacklist_state[this.res_id];
                }
                else {
                    blacklist_state[this.res_id] = is_blacklisted = this.value;
                }

                if (this.recordData.blacklist_reason != undefined && this.recordData.blacklist_reason) {
                    var no_html_reason = $( $.parseHTML(this.recordData.blacklist_reason) ).text();
                    this.$el.html($('<div class="div_toogle_blacklist_'+ this.res_id +'" title="' + no_html_reason + '">').addClass("toggle_blacklist_"+ this.res_id).css({
                        backgroundColor: is_blacklisted ? this.blacklistedColor : this.whitelistColor
                    }));
                }
                else
                {
                    this.$el.html($('<div class="div_toogle_blacklist_'+ this.res_id +'">').addClass("toggle_blacklist_"+ this.res_id).css({
                        backgroundColor: is_blacklisted ? this.blacklistedColor : this.whitelistColor
                    }));
                }
            },
            _onClick: function(event) {
                if (this.model != 'mail.mass_mailing.list_contact_rel'){
                    event.stopPropagation();
                    this._rpc({
                            model: this.model,
                            method: 'toggle_blacklist',
                            args: [this.res_id],
                        })
                        .then(function (ret) {
                              if (ret[1] != 'not_found') {
                                  var color = ret[1] ? 'red' : 'green';
                                  // Get all the divs on the screen related to the record to update them all.
                                  var blacklist_widgets = document.getElementsByClassName('toggle_blacklist_' + ret[0]);
                                  for (var i = 0; i < blacklist_widgets.length; i++) {
                                    blacklist_widgets[i].style.backgroundColor = color;
                                  }
                                  blacklist_state[ret[0]] = ret[1];
                              }
                        });
                }
            },
        });

    fieldRegistry.add('blacklist_widget', blacklist_widget);
});