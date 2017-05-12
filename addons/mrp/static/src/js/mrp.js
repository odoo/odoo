odoo.define('mrp.mrp_state', function (require) {
"use strict";

var core = require('web.core');
var common = require('web.form_common');
var Model = require('web.Model');
var time = require('web.time');
var utils = require('web.utils');
var FieldBinaryFile = core.form_widget_registry.get('binary');

var _t = core._t;


var SetBulletStatus = common.AbstractField.extend(common.ReinitializeFieldMixin,{
    init: function(field_manager, node) {
        this._super(field_manager, node);
        this.classes = this.options && this.options.classes || {};
    },
    render_value: function() {
        this._super.apply(this, arguments);
        if (this.get("effective_readonly")) {
            var bullet_class = this.classes[this.get('value')] || 'default';
            if (this.get('value')){
                var title = this.get('value') == 'waiting'? _t('Waiting Materials') : _t('Ready to produce');
                this.$el.attr({'title': title, 'style': 'display:inline'});
                this.$el.removeClass('text-success text-danger text-default');
                this.$el.html($('<span>' + title + '</span>').addClass('label label-' + bullet_class));
            }
        }
    },
});

var TimeCounter = common.AbstractField.extend(common.ReinitializeFieldMixin, {
    start: function() {
        this._super();
        var self = this;
        this.field_manager.on("view_content_has_changed", this, function () {
            self.render_value();
        });
    },
    start_time_counter: function(){
        var self = this;
        clearTimeout(this.timer);
        if (this.field_manager.datarecord.is_user_working) {
            this.duration += 1000;
            this.timer = setTimeout(function() {
                self.start_time_counter();
            }, 1000);
        } else {
            clearTimeout(this.timer);
        }
        this.$el.html($('<span>' + moment.utc(this.duration).format("HH:mm:ss") + '</span>'));
    },
    render_value: function() {
        this._super.apply(this, arguments);
        var self = this;
        this.duration;
        var productivity_domain = [['workorder_id', '=', this.field_manager.datarecord.id], ['user_id', '=', self.session.uid]];
        new Model('mrp.workcenter.productivity').call('search_read', [productivity_domain, []]).then(function(result) {
            if (self.get("effective_readonly")) {
                self.$el.removeClass('o_form_field_empty');
                var current_date = new Date();
                self.duration = 0;
                _.each(result, function(data) {
                    self.duration += data.date_end ? self.get_date_difference(data.date_start, data.date_end) : self.get_date_difference(time.auto_str_to_date(data.date_start), current_date);
                });
                self.start_time_counter();
            }
        });
    },
    get_date_difference: function(date_start, date_end) {
        var difference = moment(date_end).diff(moment(date_start));
        return moment.duration(difference);
    },
});

var FieldPdfViewer = FieldBinaryFile.extend({
    template: 'FieldPdfViewer',
    init: function(){
        this._super.apply(this, arguments);
        this.PDFViewerApplication = false;
    },
    get_uri: function(){
        var query_obj = {
            model: this.view.dataset.model,
            field: this.name,
            id: this.view.datarecord.id
        };
        var query_string = $.param(query_obj);
        var url = encodeURIComponent('/web/image?' + query_string);
        var viewer_url = '/web/static/lib/pdfjs/web/viewer.html?file=';
        return viewer_url + url;
    },
    on_file_change: function(ev) {
        this._super.apply(this, arguments);
        if(this.PDFViewerApplication){
            var files = ev.target.files;
            if (!files || files.length === 0) {
              return;
            }
            var file = files[0];
            // TOCheck: is there requirement to fallback on FileReader if browser don't support URL
            this.PDFViewerApplication.open(URL.createObjectURL(file), 0);
        }
    },
    render_value: function() {
        var $pdf_viewer = this.$('.o_form_pdf_controls').children().add(this.$('.o_pdfview_iframe')),
            $select_upload_el = this.$('.o_select_file_button').first(),
            $iFrame = this.$('.o_pdfview_iframe'),
            value = this.get('value'),
            self = this;

        var bin_size = utils.is_bin_size(value);
        $iFrame.on('load', function(){
            self.PDFViewerApplication = this.contentWindow.window.PDFViewerApplication;
            self.disable_buttons(this);
        });
        if (this.get("effective_readonly")) {
            if (value) {
                this.$el.off('click'); // off click event(on_save_as) of FieldBinaryFile
                $iFrame.attr('src', this.get_uri());
            }
        } else {
            if (value) {
                $pdf_viewer.removeClass('o_hidden');
                $select_upload_el.addClass('o_hidden');
                if(bin_size){
                    $iFrame.attr('src', this.get_uri());
                }
            } else {
                $pdf_viewer.addClass('o_hidden');
                $select_upload_el.removeClass('o_hidden');
            }
        }
    },
    disable_buttons: function(iframe){
        if (this.get("effective_readonly")){
            $(iframe).contents().find('button#download').hide();
        }
        $(iframe).contents().find('button#openFile').hide();
    }

});
core.form_widget_registry.add('bullet_state', SetBulletStatus)
                         .add('mrp_time_counter', TimeCounter)
                         .add('pdf_viewer', FieldPdfViewer);
});
