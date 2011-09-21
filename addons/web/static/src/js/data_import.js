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
        this._super(parent, {});
    },
    start: function() {
        var self = this;
        this._super();
        this.open({
            modal: true,
            width: '70%',
            height: 'auto',
            position: 'top',
            buttons: [
                {text: "Close", click: function() { self.stop(); }},
                {text: "Import File", click: function() { self.do_import(); }, 'class': 'oe-dialog-import-button'}
            ],
            close: function(event, ui) {
                self.stop();
            }
        });
        this.toggle_import_button(false);
        this.$element.find('#csvfile').change(this.on_autodetect_data);
        this.$element.find('fieldset').change(this.on_autodetect_data);
        this.$element.find('fieldset legend').click(function() {
            $(this).next().toggle();
        });
    },
    toggle_import_button: function (newstate) {
        this.$dialog.dialog('widget')
                .find('.oe-dialog-import-button')
                .button('option', 'disabled', !newstate);
    },
    do_import: function() {
        if(!this.$element.find('#csvfile').val()) { return; }
        jsonp(this.$element.find('#import_data'), {
            url: '/web/import/import_data'
        }, this.on_import_results);
    },
    on_autodetect_data: function() {
        if(this.$element.find("#res td")){
            this.$element.find("#res td").remove();
            this.$element.find("#imported_success").css('display','none');
        }
        if(!this.$element.find('#csvfile').val()) { return; }
        jsonp(this.$element.find('#import_data'), {
            url: '/web/import/detect_data'
        }, this.on_import_results);
    },
    on_import_results: function(results) {
        this.$element.find('#result, #success').empty();
        var result_node = this.$element.find("#result");
        var records = {};

        if (results['records']) {
            records = {'header': results['header'], 'sel': results['all_fields'], 'row': results['records']};
            result_node.append(QWeb.render('ImportView-result', {'records': records}));
        } else if (results['error']) {
            result_node.append(QWeb.render('ImportView-result', {'error': results['error']}));
        } else if (results['success']) {
            self.stop();
            if (this.widget_parent.widget_parent.active_view == "list") {
                this.widget_parent.reload_content();
            }
        }
        this.do_check_req_field(results['req_field']);
        this.on_change_check(results['req_field']);
        var self = this;
        this.$element.find("td #sel_field").change(function() {
            self.on_change_check(results['req_field']);
        });
    },
    on_change_check: function (req_field){
        var self = this;
        self.$element.find("#message, #msg").remove();
        var selected_flds = self.$element.find("td #sel_field option:selected");
        _.each(selected_flds, function(fld) {
            if (fld.index != 0) {
                var res = self.$element.find("td #sel_field option:selected[value='" + fld.value + "']");
                if (res.length == 1) {
                    res.parent().removeClass("duplicate_fld").addClass("select_fld");
                } else if (res.length > 1) {
                    res.parent().removeClass("select_fld").addClass("duplicate_fld");
                    res.parent().focus();
                }
            } else {
                var elem = self.$element.find("td #sel_field option:selected[value='" + fld.value + "']");
                elem.parent().removeClass("duplicate_fld").addClass("select_fld");
            }
        });
        if (self.$element.find(".duplicate_fld").length) {
            this.$element.find("#result").before('<div id="msg" style="color:red">*Selected column should not be same.</div>');
            this.toggle_import_button(false);
        } else {
            self.$element.find("#msg").remove();
            this.toggle_import_button(true);
        }
        self.do_check_req_field(req_field);
    },
    do_check_req_field: function(req_fld) {
        if (!req_fld.length) { return; }

        this.$element.find("#message").remove();
        var sel_fields = _.map(this.$element.find("td #sel_field option:selected"), function(fld) {
            return fld['text']
        });
        var required_fields = _.filter(req_fld, function(fld) {
            return !_.contains(sel_fields, fld)
        });
        if (required_fields.length) {
            this.$element.find("#result").before('<div id="message" style="color:red">*Required Fields are not selected : ' + required_fields + '.</div>');
            this.toggle_import_button(false);
        } else {
            this.$element.find("#message").remove();
            this.toggle_import_button(true);
        }
    },
    stop: function() {
        $(this.$dialog).remove();
        this._super();
    }
});
};
