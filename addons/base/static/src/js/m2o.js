openerp.base.m2o = function(openerp){

    openerp.base.m2o = openerp.base.Controller.extend({
        init: function(view_manager, element_id, model, dataset, session){
            this._super(element_id, model, dataset, session);

            this.view_manager = view_manager;
            this.session = session;
            this.element = element_id.find('input');
            this.button = element_id.find('span');
            this.dataset = dataset;
            this.cache = {};
            var lastXhr;
            this.$input;
            this.relation = model;
            this.result_ids = [];
            this.create_option = jQuery('#'+this.element.attr('name')+ '_open');
            var self = this;

            this.$input = this.element.autocomplete ({
                source: function(request, response){
                    self.getSearch_Result(request, response);
                    return;
                },
                select: function(event, ui){
                    self.getSelected_Result(event, ui);
                },
                minLength: 0,
                focus: function(event, ui) {
                    self.gotFocus(event, ui);
                }
            });

            this.button.button({
                icons: {
                    primary: "ui-icon-triangle-1-s"},
                    text: false
            })
            .click(function() {
                // close if already visible
                if (self.$input.autocomplete("widget").is(":visible")) {
                    self.$input.autocomplete( "close" );
                    return;
                }
                $(this).blur();
                self.$input.autocomplete("search", "" );
                self.$input.focus();
            });
        },

        getSearch_Result: function(request, response) {
            var search_val = request.term;
            if (search_val in this.cache) {
                response(this.cache[search_val]);
                return;
            }
            var self = this;
            //pass request to server
            lastXhr = this.dataset.name_search(search_val, function(obj, status, xhr){
                var result = obj.result;
                var values = [];

                $.each(result, function(i, val){
                    values.push({
                        value: val[1],
                        id: val[0],
                        orig_val: val[1]
                    });
                    self.result_ids.push(result[i][0]);
                });

                if (values.length > 7) {
                    values = values.slice(0, 7);
                }
                values.push({'value': 'More...', id: 'more', orig_val:''},
                            {'value': 'Create..'+search_val, id: 'create', orig_val: ''});
                self.cache[search_val] = values;
                response(values);
            });
        },

        getSelected_Result: function(event, ui) {
            ui.item.value = ui.item.orig_val? ui.item.orig_val : this.element.data( "autocomplete" ).term;
            if (ui.item.id == 'more') {
                this.dataset.ids = this.result_ids;
                this.dataset.count = this.dataset.ids.length;
                this.dataset.domain = this.result_ids.length ? [["id", "in", this.dataset.ids]] : []
                this.element.val('');
                var pop = new openerp.base.form.Many2XSelectPopup(null, this.session);
                pop.select_element(this.relation, this.dataset);
                return;
            }

            if (ui.item.id == 'create') {
                this.openRecords(event, ui)
            }
            this.element.attr('m2o_id', ui.item.id);
        },

        gotFocus: function(event, ui) {
            if (ui.item.id == ('create')) {
                return true;
            }
            ui.item.value = this.element.data("autocomplete").term.length ?
                this.element.val() + '[' + ui.item.orig_val.substring(this.element.data("autocomplete").term.length) + ']' : this.lastSearch;
        },

        openRecords: function(event, ui) {
            var val = this.element.val();
            var self = this
                this.dataset.create({'name': ui.item.value},
                    function(r){}, function(r){
                        var element_id = _.uniqueId("act_window_dialog");
                        var dialog = jQuery('<div>',
                                                {'id': element_id
                                            }).dialog({
                                                        modal: true,
                                                        minWidth: 800
                                                     });
                        self.element.val('');
                        var event_form = new openerp.base.FormView(self.view_manager, self.session, element_id, self.dataset, false);
                        event_form.start();
                });
                self.$input.val(self.element.data( "autocomplete" ).term);
                return true;
        }
    });
}
