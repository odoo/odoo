openerp.base.m2o = function(openerp){

    openerp.base.m2o = openerp.base.Controller.extend({
        init: function(view_manager, element_id, model, dataset, session){
            this._super(element_id, model, dataset, session);

            this.view_manager = view_manager
            this.session = session;
            this.element = element_id.find('input');
            this.dataset = dataset;
            var cache = {};
            var lastXhr;
            this.relation = model;
            this.result_ids = []
            var self = this

            var $input = this.element.autocomplete({

                source: function(request, response){
                    var search_val = request.term;
                    if (search_val in cache) {
                        response(cache[search_val]);
                        return;
                    }
                    //pass request to server
                    lastXhr = self.dataset.name_search(search_val, function(obj, status, xhr){
                        var result = obj.result
                        var values = [];
                        if (!result.length) {
                            values.push({'value': 'Create...', id: 'create'})
                        }

                        $.each(result, function(i, val){
                            values.push({
                                value: val[1],
                                id: val[0],
                                orig_val: val[1]
                            });
                            self.result_ids.push(result[i][0])
                        });

                        if (values.length > 10) {
                            values = values.slice(0, 10);
                            values.push({'value': 'More...', id: 'more'})
                        }
                        //process response
                        cache[search_val] = values;
                        response(values);
                    });
                    return;
                },

                select: function(event, ui){
                    ui.item.value = ui.item.orig_val? ui.item.orig_val : self.element.data( "autocomplete" ).term
                    if (ui.item.id == 'more') {
                        self.dataset.ids = self.result_ids;
                        self.dataset.count = self.dataset.ids.length;
                        self.dataset.domain = []
                        self.element.val('')
                        var pop = new openerp.base.form.Many2XSelectPopup(null, self.session);
                        pop.select_element(self.relation, self.dataset);
                        return;
                    }

                    if (ui.item.id == 'create') {
                        var val = self.element.val()
                        self.dataset.create({'name': ui.item.value},
                            function(r){}, function(r){
                                var element_id = _.uniqueId("act_window_dialog");
                                var dialog = jQuery('<div>',
                                                        {'id': element_id
                                                    }).dialog({
                                                                modal: true,
                                                                minWidth: 800
                                                             });
                                self.element.val('')
                                var event_form = new openerp.base.FormView(self.view_manager, self.session, element_id, self.dataset, false);
                                event_form.start();
                        });
                        $input.val(self.element.data( "autocomplete" ).term);
                        return true;
                    }
                    self.element.attr('m2o_id', ui.item.id);
                },

                minLength: 0,

                focus: function(event, ui) {
                    if (ui.item.id == ('create')) {
                        return true;
                    }
                    ui.item.value = self.element.data("autocomplete").term.length ? self.element.val() + '[' + ui.item.orig_val.substring(self.element.data("autocomplete").term.length) + ']' : this.lastSearch
                }

            });

            $("<div type='button' class='ui_combo'>&nbsp;</div>")
                    .attr("tabIndex", -1)
                    .attr("title", "Show All Items")
                    .insertAfter($input)
                    .button({
                        icons: {
                            primary: "ui-icon-triangle-1-s"
                        },
                        text: false
                    })
                    .removeClass("ui-corner-all")
                    .addClass("ui-corner-right ui-button-icon")
                    .click(function() {
                        // close if already visible
                        if ($input.autocomplete("widget").is(":visible")) {
                            $input.autocomplete( "close" );
                            return;
                        }
                        $(this).blur();
                        $input.autocomplete("search", "" );
                        $input.focus();
                    });
        }
    });
}
