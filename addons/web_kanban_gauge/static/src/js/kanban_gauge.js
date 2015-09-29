odoo.define('web_kanban_gauge.widget', function (require) {
"use strict";

var core = require('web.core');
var kanban_widgets = require('web_kanban.widgets');

var AbstractField = kanban_widgets.AbstractField;
var fields_registry = kanban_widgets.registry;
var _t = core._t;

/**
 * Kanban widgets: GaugeWidget
 * options
 * - max_value: maximum value of the gauge [default: 100]
 * - max_field: get the max_value from the field that must be present in the
 *              view; takes over max_value
 * - gauge_value_field: if set, the value displayed below the gauge is taken
                        from this field instead of the base field used for
                        the gauge. This allows to display a number different
                        from the gauge.
 * - force_set: is value is 0, display a text 'Click to set' [default: True]
 * - label: lable of the gauge, displayed below the gauge value
 * - title: title of the gauge, displayed on top of the gauge
 * - on_change: action to call when cliking and setting a value
 * - on_click_label: optional label of the input displayed when clicking
 *
 */

var GaugeWidget = AbstractField.extend({
    className: "oe_gauge",

    start: function() {
        var self = this;
        var parent = this.getParent();
        // parameters
        var max_value = this.options.max_value || 100;
        if (this.options.max_field) {
            max_value = this.getParent().record[this.options.max_field].raw_value;
        }
        var label = this.options.label || "";
        if (this.options.label_field) {
            label = this.getParent().record[this.options.label_field].raw_value;
        }
        var title = this.$node.html() || this.field.string;
        // current gauge value
        var val = this.field.raw_value;
        if (_.isArray(JSON.parse(val))) {
            val = JSON.parse(val);
        }
        var value = _.isArray(val) && val.length ? val[val.length-1]['value'] : val;
        // displayed value under gauge
        var gauge_value = value;
        if (this.options.gauge_value_field) {
            gauge_value = this.getParent().record[this.options.gauge_value_field].raw_value;
        }
        // var unique_id = _.uniqueId("JustGage");

        this.$el.empty().attr('style', this.$node.attr('style') + ';position:relative; display:inline-block;');
        this.gage = new JustGage({
            parentNode: this.$el[0],
            // id: unique_id,
            value: value,
            title: title,
            min: 0,
            max: max_value,
            relativeGaugeSize: true,
            humanFriendly: true,
            titleFontColor: '#333333',
            valueFontColor: '#333333',
            labelFontColor: '#000',
            label: label,
            levelColors: self.options.levelcolors || [
                "#ff0000",
                "#f9c802",
                "#a9d70b"
            ],
        });
        this.gage.refresh(value, max_value);

        var flag_open = false;
        if (this.options.on_change) {
            var $svg = this.$el.find('svg');

            this.$el.click(function (event) {
                event.stopPropagation();
                flag_open = false;
                if (!parent.view.is_action_enabled('edit')) {
                    return;
                }
                // fade widget
                $svg.fadeTo(0, 0.2);

                // add input
                if (!self.$el.find(".oe_justgage_edit").size()) {
                    var $div = $('<div class="oe_justgage_edit" style="z-index:1"/>');
                    $div.css({
                        'text-align': 'center',
                        'position': 'absolute',
                        'width': self.$el.outerWidth() + 'px',
                        'top': (self.$el.outerHeight()/2-5) + 'px'
                    });
                    var $input = $('<input/>').val(gauge_value);
                    $input.css({
                        'text-align': 'center',
                        'margin': 'auto',
                        'width': ($svg.outerWidth()-40) + 'px'
                    });
                    $div.append($input);
                    if (self.options.on_click_label) {
                        var $post_input = $('<span style="color: #000000;">' + self.options.on_click_label + '</span>');
                        $div.append($post_input);
                    }
                    self.$el.prepend($div);

                    $input.focus()
                        .keydown(function (event) {
                            event.stopPropagation();
                            if(isNaN($input.val())){
                                self.do_warn(_t("Wrong value entered!"), _t("Only Integer Value should be valid."));
                                $div.remove();
                                $svg.fadeTo(0, 1);
                            } else {
                                if (event.keyCode == 13 || event.keyCode == 9) {
                                    if ($input.val() != value) {
                                        $svg.fadeTo(0, 1);
                                        parent.view.dataset.call(self.options.on_change, [parent.id, $input.val()]).then(function () {
                                            parent.do_reload();
                                        });
                                    } else {
                                        $svg.fadeTo(0, 1);
                                        $div.remove();
                                    }
                                }
                            }
                        })
                        .click(function (event) {
                            event.stopPropagation();
                            flag_open = false;
                        })
                        .blur(function () {
                            if(!flag_open) {
                                self.$el.find(".oe_justgage_edit").remove();
                                $svg.fadeTo(0, 1);
                            } else {
                                $svg.fadeTo(0, 1);
                                flag_open = false;
                                setTimeout(function () {$input.focus();}, 0);
                            }
                        });
                }
            }).mousedown(function () {
                flag_open = true;
            });

            if (this.options.force_set && !+input_value) {
                $svg.fadeTo(0, 0.3);
                var $div = $('<div/>').text(_t("Click to change value"));
                $div.css(css);
                this.$el.append($div);
            }
        }
    },
});

fields_registry.add("gauge", GaugeWidget);

});
