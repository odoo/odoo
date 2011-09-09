openerp.web.data_import = function(openerp) {
var QWeb = openerp.web.qweb;
/**
 * Safari does not deal well at all with raw JSON data being returned. As a
 * result, we're going to cheat by using a pseudo-jsonp: instead of getting
 * JSON data in the iframe, we're getting a ``script`` tag which consists of a
 * function call and the returned data (the json dump).
 *
 * The function is an auto-generated name bound to ``window``, which calls
 * back into the callback provided here.
 *
 * @param {Object} form the form element (DOM or jQuery) to use in the call
 * @param {Object} attributes jquery.form attributes object
 * @param {Function} callback function to call with the returned data
 */
function jsonp(form, attributes, callback) {
    var options = {jsonp: _.uniqueId('import_callback_')};
    window[options.jsonp] = function () {
        delete window[options.jsonp];
        callback.apply(null, arguments);
    };
    $(form).ajaxSubmit(_.extend({
        data: options
    }, attributes));
}
openerp.web.DataImport = openerp.web.Dialog.extend({
    template: 'ImportDataView',
    dialog_title: "Import Data",
    init: function(parent, dataset){
        this._super(parent);
        this.dataset = dataset;
    },
    start: function() {
        var self = this;
        self._super(false);
        self.template = 'ImportDataView';
        self.dialog_title = "Import Data"
        self.open({
                    modal: true,
                    width: '70%',
                    height: 'auto',
                    position: 'top',
                    buttons : {
                        "Close" : function() {
                            self.stop();
                          },
                        "Import File" : function() {
                                self.do_import();
                          }
                       },
                    close: function(event, ui){ self.stop();}
                   });
        this.$element.find('#csvfile').change(this.on_autodetect_data);
        this.$element.find('fieldset').change(this.on_autodetect_data);
        this.$element.find('fieldset legend').click(function () {
                $(this).next().toggle();
        });
    },
    do_import: function() {
            var self = this;
            if(!this.$element.find('#csvfile').val()) { return; }
            jsonp(this.$element.find('#import_data'), {
                url: '/web/import/import_data'
            }, this.on_import_results);
    },
    on_autodetect_data: function() {
            var self = this;
            if(this.$element.find("#res td")){
                this.$element.find("#res td").remove();
                this.$element.find("#imported_success").css('display','none');
            }
            if(!this.$element.find('#csvfile').val()) { return; }
            jsonp(this.$element.find('#import_data'), {
                url: '/web/import/detect_data'
            }, this.on_import_results);
    },
    on_import_results:function(results){
        var self = this;
        this.$element.find('#result, #success , #message').empty();

        var result_node = $("#result");
        var records = {};

        if (results['records']){
            records = {'header':results['header'],'sel':results['all_fields'],'row':results['records']};
            result_node.append(QWeb.render('ImportView-result',{'records':records}));
        }else if(results['error']){
            result_node.append(QWeb.render('ImportView-result',{'error': results['error']}));
        }else if(results['success']){
            self.stop();
            if (((this.widget_parent['fields_view']['type']) == "tree") || ((this.widget_parent['fields_view']['type']) == "list")){
                this.widget_parent.reload_content();
            }
        }
        this.do_check_req_field(results['req_field']);
        var selected_fields = [];
        this.$element.find("td #sel_field").click(function(){
            selected_fields = [];
            self.$element.find("td #sel_field option:selected").each(function(){
                selected_fields.push($(this).index());
            });
        });
        this.$element.find("td #sel_field").change(function(){
            self.$element.find("#message").empty();
            self.$element.find("td #sel_field").css('background-color','');
            self.$element.find(".ui-button-text:contains('Import File')").parent().attr("disabled",false);
            self.do_check_req_field(results['req_field']);
            var curr_selected = this.selectedIndex;
            if ((curr_selected != 0) && _.contains(selected_fields, curr_selected)){
                $(this).css('background-color','#FF6666');
                $("#message").append("*Selected column should not be same.");
                $(".ui-button-text:contains('Import File')").parent().attr("disabled",true);
            }else{
                $(this).css('background-color','');
            }
        });
    },
    do_check_req_field: function(req_fld){
        if (req_fld.length){
            var required_fields = "";
            var sel_fields = _.map(this.$element.find("td #sel_field option:selected"), function(fld){
                                return fld['text']
                            });

            required_fields =  required_fields + _.filter(req_fld, function (fld){
                                    if (!_.contains(sel_fields,fld)){
                                        return fld + "," ;
                                    }
                                });

            if (required_fields.length){
                $("#message").append("*Required Fields are not selected which is "+required_fields+". ");
                $(".ui-button-text:contains('Import File')").parent().attr("disabled",true);
            }else{
                $(".ui-button-text:contains('Import File')").parent().attr("disabled",false);
            }
        }
    },
    stop: function() {
        $(this.$dialog).remove();
        this._super();
    }
});
};
