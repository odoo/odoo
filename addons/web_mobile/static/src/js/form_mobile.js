openerp.web_mobile.form_mobile = function (openerp) {
openerp.web_mobile.FormView = openerp.base.Controller.extend({
    init: function(session, element_id, list_id, action) {
        this._super(session, element_id);
        this.list_id = list_id;
        this.action = action;
    },
    start: function() {
        var self = this;
        id = this.list_id;
        model = this.action.res_model;
        view_id = this.action.views[1][0];

        this.dataset = new openerp.base.DataSetSearch(this.session, this.action.res_model, null, null);
        this.dataset.read_slice([], 0, false, function (result) {
            for (var i = 0; i < result.length; i++) {
                if (result[i].id == id) {
                    var data = result[i];
                }
            }
            self.rpc("/base/formview/load", {"model": model, "view_id": view_id }, function (result) {
                var fields = result.fields_view.fields;
                var view_fields = result.fields_view.arch.children;
                var get_fields = self.get_fields(view_fields);
                var selection = new openerp.web_mobile.Selection();

                for (var j = 0; j < view_fields.length; j++) {
                    if (view_fields[j].tag == 'notebook') {
                        var notebooks = view_fields[j];
                    }
                }
                $("#oe_header").find("h1").html(result.fields_view.arch.attrs.string);
                self.$element.html(QWeb.render("FormView", {'get_fields': get_fields, 'notebooks': notebooks || false, 'fields' : fields, 'values' : data }));

                    self.$element.find('select').change(function(ev){
                        selection.on_select_option(ev);
                    });

                    self.$element.find('a').click(function(){

                        for (var k = 0; k < notebooks.children.length; k++) {

                            var text = $(this).find('.ui-btn-text').text();
                            var next = $(this).next();
                            var span = $(this).find('span .ui-icon');
                            var content_expanded_class = "ui-collapsible-content ui-collapsible-content-expanded";
                            var content_collapsed_class = "ui-collapsible-content ui-collapsible-content-collapsed";
                            var expanded_class = "ui-collapsible-content-expanded";
                            var collapsed_class = "ui-collapsible-content-collapsed";
                            var plus_class = "ui-icon-plus";
                            var minus_class = "ui-icon-minus";

                            if (notebooks.children[k].attrs.string == $.trim(text)) {
                                get_fields = self.get_fields(notebooks.children[k].children);

                                $(this).parents().find('form').find('div').each( function() {
                                    var prev = $(this).prev();
                                    var trim_class = $.trim($(this).attr('class'));
                                    if (trim_class == content_expanded_class || trim_class == content_collapsed_class) {
                                        prev.removeClass('ui-btn-active');

                                        if ($.trim(prev.find('.ui-btn-text').text()) != notebooks.children[k].attrs.string) {
                                            prev.find('span .ui-icon').removeClass(minus_class);
                                            prev.find('span .ui-icon').addClass(plus_class);
                                            $(this).removeClass(expanded_class);
                                            $(this).addClass(collapsed_class);
                                        }
                                    }
                                });

                                if (next.hasClass(content_collapsed_class)) {
                                    span.removeClass(plus_class);
                                    span.addClass(minus_class);
                                    next.removeClass(collapsed_class);
                                    next.addClass(expanded_class);
                                }
                                else if (next.hasClass(content_expanded_class)) {
                                    span.removeClass(minus_class);
                                    span.addClass(plus_class);
                                    next.removeClass(expanded_class);
                                    next.addClass(collapsed_class);
                                }
                                if (!next.find('.detail').html().length) {

                                    for (var i = 0; i < get_fields.length; i++) {

                                        if (fields[get_fields[i].attrs.name].type == 'one2many'){
                                            var get_fields_test = self.get_fields(fields[get_fields[i].attrs.name].views.form.arch.children);
                                            var fields_test = fields[get_fields[i].attrs.name]['views'].form.fields;
                                            next.find('.detail').append(QWeb.render("FormView", {'get_fields': get_fields_test,'fields' : fields_test, 'values' : data }));
                                        }
                                    }
                                    next.find('.detail').append(QWeb.render("FormView", {'get_fields': get_fields,'fields' : result.fields_view.fields, 'values' : data }));
                                }
                            }
                        }

                        self.$element.find('select').change(function(ev){
                            selection.on_select_option(ev);
                        });
                    });
                });
        });
    },
    get_fields: function(view_fields, fields) {
        this.fields = fields || [];
        for (var i=0; i < view_fields.length; i++){
            if (view_fields[i].tag == 'field') {
                this.fields.push(view_fields[i]);
            }
            if (view_fields[i].tag == 'group') {
                this.get_fields(view_fields[i].children, this.fields);
            }
        }
        return this.fields;
    }
});
}