openerp.web_kanban_gauge = function (instance) {

/**
 * Kanban widgets: GaugeWidget
 *
 */
var _t = instance.web._t,
   _lt = instance.web._lt;

instance.web_kanban.GaugeWidget = instance.web_kanban.AbstractField.extend({
    className: "oe_gauge",

    start: function() {
        var self = this;
        var parent = this.getParent();
        var max = 100;
        if (this.options.max_field) {
            max = this.getParent().record[this.options.max_field].raw_value;
        }
        var label = this.options.label || "";
        if (this.options.label_field) {
            label = this.getParent().record[this.options.label_field].raw_value;
        }
        var val = this.field.value;
        var value = _.isArray(val) && val.length ? val[val.length-1]['value'] : val;
        var title = this.$node.html() || this.field.string;
        // var unique_id = _.uniqueId("JustGage");

        this.$el.empty()
            .attr('style', this.$node.attr('style') + ';position:relative; display:inline-block;');

        this.gage = new JustGage({
            parentNode: this.$el[0],
            // id: unique_id,
            value: value,
            title: title,
            min: 0,
            max: max,
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
        this.gage.refresh(value, max);

        var flag_open = false;
        if (this.options.action_change) {
            var $svg = this.$el.find('svg');
            var css = {
                'text-align': 'center',
                'position': 'absolute',
                'width': this.$el.outerWidth() + 'px',
                'top': (this.$el.outerHeight()/2-5) + 'px'
            };

            this.$el.click(function (event) {
                event.stopPropagation();
                flag_open = false;
                if (!parent.view.is_action_enabled('edit')) {
                    return;
                }
                if (!self.$el.find(".oe_justgage_edit").size()) {
                    $div = $('<div class="oe_justgage_edit" style="z-index:1"/>');
                    $div.css(css);
                    $input = $('<input/>').val(value);
                    $input.css({
                        'text-align': 'center',
                        'margin': 'auto',
                        'width': ($svg.outerWidth()-40) + 'px'
                    });
                    $div.append($input);
                    self.$el.prepend($div)
                    $input.focus()
                        .keydown(function (event) {
                            event.stopPropagation();
                            if(isNaN($input.val())){
                                self.do_warn(_t("Wrong value entered!"), _t("Only Integer Value should be valid."));
                                $div.remove();
                            } else {
                                if (event.keyCode == 13 || event.keyCode == 9) {
                                    if ($input.val() != value) {
                                        parent.view.dataset.call(self.options.action_change, [parent.id, $input.val()]).then(function () {
                                            parent.do_reload();
                                        });
                                    } else {
                                        $div.remove();
                                    }
                                }
                            }
                        })
                        .click(function (event) {
                            event.stopPropagation();
                            flag_open = false;
                        })
                        .blur(function (event) {
                            if(!flag_open) {
                                self.$el.find(".oe_justgage_edit").remove();
                            } else {
                                flag_open = false;
                                setTimeout(function () {$input.focus();}, 0);
                            }
                        });
                }
            }).mousedown(function () {
                flag_open = true;
            });

            if (!+value) {
                $svg.fadeTo(0, 0.3);
                $div = $('<div/>').text(_t("Click to change value"));
                $div.css(css);
                this.$el.append($div);
            }
        }
    },
});

instance.web_kanban.fields_registry.add("gauge", "instance.web_kanban.GaugeWidget");

}
