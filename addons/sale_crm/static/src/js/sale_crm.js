openerp.sale_crm = function(openerp) {

openerp.sale_crm.GaugeWidget = openerp.web_kanban.AbstractField.extend({
    className: "oe_gage",
    start: function() {
        var self = this;
        console.log("start");

        var parent = this.getParent();
        var max = this.options.max_field ? parent.record[this.options.max_field].raw_value : 100;
        var label = this.options.label_field ? parent.record[this.options.label_field].raw_value : "";
        var title = this.$node.html();
        var val = this.field.value;
        var value = _.isArray(val) && val.length ? val[val.length-1] : val;
        var unique_id = _.uniqueId("JustGage");
        
        this.$el.empty()
            .attr('style', this.$node.attr('style') + ';position:relative; display:inline-block;')
            .attr('id', unique_id);
        this.gage = new JustGage({
            id: unique_id,
            node: this.$el[0],
            title: title,
            value: value,
            min: 0,
            max: max,
            relativeGaugeSize: true,
            humanFriendly: true,
            titleFontColor: '#333333',
            valueFontColor: '#333333',
            labelFontColor: '#000',
            label: label,
            levelColors: [
                "#ff0000",
                "#f9c802",
                "#a9d70b"
            ],
        });

        var flag_open = false;
        if (self.options.action_change) {
            self.$el.click(function (event) {
                event.stopPropagation();
                flag_open = false;
                if (!parent.view.is_action_enabled('edit')) {
                    return;
                }
                if (!self.$el.find(".oe_justgage_edit").size()) {
                    var $svg = self.$el.find('svg');
                    $div = $('<div class="oe_justgage_edit" style="text-align: center; z-index: 1; position: absolute; width: ' + $svg.outerWidth() + 'px; top: ' + ($svg.outerHeight()/2-5) + 'px;"/>');
                    $input = $('<input style="text-align: center; width: ' + ($svg.outerWidth()-40) + 'px; margin: auto;"/>').val(value);
                    $div.append($input);
                    self.$el.prepend($div)
                    $input.focus()
                        .keydown(function (event) {
                            event.stopPropagation();
                            if (event.keyCode == 13 || event.keyCode == 9) {
                                if ($input.val() != value) {
                                    parent.view.dataset.call(self.options.action_change, [parent.id, $input.val()]).then(function () {
                                        parent.do_reload();
                                    });
                                } else {
                                    $div.remove();
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
        }
    },
});
openerp.web_kanban.fields_registry.add("gage", "openerp.sale_crm.GaugeWidget");

};
