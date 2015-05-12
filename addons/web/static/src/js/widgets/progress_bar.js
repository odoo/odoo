odoo.define('web.ProgressBar', function (require) {
"use strict";

var Widget = require('web.Widget');
var core = require('web.core');
var QWeb = core.qweb;
var kanban_common = require('web_kanban.common');
var utils = require('web.utils');
var AbstractField = kanban_common.AbstractField;
var fields_registry = kanban_common.registry;
var _t = core._t;


/**
 * Kanban widgets: ProgressBar
 * options
 * - editable: boolean if current_value is editable
 * - editable_value: if set, get the editable_value from the field that must be present in the view
 *      [default: current_value]
 * - current_value: get the current_value from the field that must be present in the view
 * - max_value: get the max_value from the field that must be present in the view
 * - title: title of the gauge, displayed on top of the gauge
 * - on_change: action to call when cliking and setting a value
 *
 */

var ProgressBar = AbstractField.extend({
    template: "ProgressBar",

    init: function (parent, field, node) {
        this._super(parent, field, node);
        var editable = this.options.editable;
        var on_change = this.options.on_change;
        var title = this.options.title;
        var current_value = this.getParent().record[this.options.current_value].raw_value;
        var editable_value = current_value;
        if (editable && this.options.editable_value){
            editable_value = this.getParent().record[this.options.editable_value].raw_value;
        }
        var max_value = this.getParent().record[this.options.max_value].raw_value;

        this.state = {
            editable: editable,
            on_change: on_change,
            title: title,
            current_value: current_value,
            max_value: max_value,
            editable_value: editable_value,
            width_complete : 0,
            width_over : 0,
        };

        var current_value = this.state.current_value;
        var max_value = this.state.max_value;
        if (current_value <= max_value){
            this.state.width_complete = current_value/max_value * 100;
        }
        else {
            this.state.width_complete = max_value/current_value * 100;
            this.state.width_over = (current_value - max_value) / current_value * 100;
        }
    },

    start: function () {

        var self = this;

        this.$el.click(function (event){
            var parent = self.getParent();
            var value = self.state.editable_value || self.state.current_value;

            event.stopPropagation();

            if (!parent.view.is_action_enabled('edit')) {
                return;
            }
            if (!self.state.editable) {
                return;
            }

            // add input
            if (!self.$el.find(".o_progress_bar_edit").size()) {
                var $div = $('<div class="o_progress_bar_edit" style="z-index:1"/>');
                $div.css({
                    'text-align': 'center',
                    'position': 'absolute',
                    'width': $(this).outerWidth() + 'px',
                });
                var $input = $('<input/>').val(value);
                $input.css({
                    'text-align': 'center',
                    'margin': 'auto',
                });
                $div.append($input);
                $(this).prepend($div);

                $input.focus()
                    .keydown(function (event) {
                        event.stopPropagation();
                        if(isNaN($input.val())){
                            self.do_warn(_t("Wrong value entered!"), _t("Only Integer Value should be valid."));
                            $div.remove();
                        } else {
                            if (event.keyCode == 13 || event.keyCode == 9) {
                                if ($input.val() != value) {
                                    parent.view.dataset.call(self.state.on_change, [parent.id, $input.val()]).then(function () {
                                        parent.do_reload();
                                    });
                                } else {
                                    $div.remove();
                                }
                            }
                        }
                    })
            }
        });

        return this._super();
    },

    _format_number: function(number) {
        return utils.human_number(number, this.type)
    },
});

fields_registry.add("progress", ProgressBar);

});