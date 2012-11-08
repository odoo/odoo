openerp.web_tests = function (instance) {
    instance.web.client_actions.add(
        'buncha-forms', 'instance.web_tests.BunchaForms');
    instance.web_tests = {};
    instance.web_tests.BunchaForms = instance.web.Widget.extend({
        init: function (parent) {
            this._super(parent);
            this.dataset = new instance.web.DataSetSearch(this, 'test.listview.relations');
            this.form = new instance.web.FormView(this, this.dataset, false, {
                action_buttons: false,
                pager: false
            });
            this.form.registry = instance.web.form.readonly;
        },
        render: function () {
            return '<div class="oe_bunchaforms"></div>';
        },
        start: function () {
            $.when(
                this.dataset.read_slice(),
                this.form.appendTo(this.$el)).done(this.on_everything_loaded);
        },
        on_everything_loaded: function (slice) {
            var records = slice[0].records;
            if (!records.length) {
                this.form.trigger("load_record", {});
                return;
            }
            this.form.trigger("load_record", records[0]);
            _(records.slice(1)).each(function (record, index) {
                this.dataset.index = index+1;
                this.form.reposition($('<div>').appendTo(this.$el));
                this.form.trigger("load_record", record);
            }, this);
        }
    });
};
