openerp.sale_crm = function(openerp) {

openerp.sale_crm.GaugeWidget = openerp.web_kanban.AbstractField.extend({
    className: "oe_gage",
    start: function() {
        var max = 100;
        if (this.options.max_field) {
            max = this.getParent().record[this.options.max_field].raw_value;
        }
        var label = "";
        if (this.options.label_field) {
            label = this.getParent().record[this.options.label_field].raw_value;
        }
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
    },
});
openerp.web_kanban.fields_registry.add("gage", "openerp.sale_crm.GaugeWidget");

};
