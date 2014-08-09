openerp.marcos_dgii = function (instance) {

    var _t = instance.web._t;
    var QWeb = instance.web.qweb;

    instance.marcos_dgii = {}

    instance.marcos_dgii.GetIpfBook = instance.web.form.FormWidget.extend({
        template: "extract_ipfbook",
        start: function() {
            var self = this;

            var dgii_sale_book = new instance.web.Model("dgii.sale_book");

            self.$el.click(function() {
                var branch = self.field_manager.get_field_value("branch");
                dgii_sale_book.call("get_ipf_proxy", [branch], {context: new instance.web.CompoundContext()}).then(function(result) {

                // ipf book api
                // http://192.168.1.242:8080/ipf/api/get_monthly_book?year=2014&month=1&branch=12
                console.log(result);
                var data = {
                    year: self.field_manager.get_field_value("year"),
                    month: self.field_manager.get_field_value("month"),
                    branch: result.branch
                };
                var id = self.field_manager.datarecord.id;

                $.ajax({
                    url: "http://"+result.proxy,
                    data: data,
                    dataType:'jsonp',
                    success: function(book) {
                        self.save_book(book, id)
                    }

                });

                });

            });
        },
        save_book: function(book, id) {

            var dgii_sale_book = new instance.web.Model("dgii.sale_book");
            dgii_sale_book.call("save_book", [book, id], {context: new instance.web.CompoundContext()}).then(function(result) {
                if (result === true){
                    alert("El libro se ha generado exitosamente! ya puede descargarlo. ");
                    location.reload();
                }

            });

        }
    });

    instance.web.form.custom_widgets.add("getipfproxy", "instance.marcos_dgii.GetIpfBook");



    instance.marcos_dgii.PrintZReport = instance.web.form.FormWidget.extend({
        template: "print_z_report",
        start: function() {
            var self = this;

                self.$el.click(function(){
                    var marcos_z_report = new instance.web.Model("marcos.z.report");
                    var filter_type     = self.field_manager.get_field_value("filter_type");
                    var period_from     = self.field_manager.get_field_value("period_from");
                    var period_to       = self.field_manager.get_field_value("period_to");
                    var sequence_from   = self.field_manager.get_field_value("sequence_from");
                    var sequence_to     = self.field_manager.get_field_value("sequence_to");
                    marcos_z_report.call("get_host",
                        [filter_type, period_from, period_to, sequence_from, sequence_to], {context: new instance.web.CompoundContext()}).then(function(result) {
                            console.log(result);
                            $.ajax({
                                url: "http://"+result.host,
                                data: result.data,
                                dataType:'jsonp'
//                                success: function(result) {console.log(result)}
                            });

                    });
            });
        }
    })

    instance.web.form.custom_widgets.add("printzreport", "instance.marcos_dgii.PrintZReport");
};