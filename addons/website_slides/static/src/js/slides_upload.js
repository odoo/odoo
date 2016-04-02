/*global $, _, PDFJS */
odoo.define('website_slides.upload', function (require) {
"use strict";

var ajax = require('web.ajax');
var core = require('web.core');
var Widget = require('web.Widget');
var base = require('web_editor.base');
var slides = require('website_slides.slides');
var website = require('website.website');

var qweb = core.qweb;
var _t = core._t;

if(!$('.oe_slide_js_upload').length) {
    return $.Deferred().reject("DOM doesn't contain '.oe_slide_js_upload'");
}

ajax.loadXML('/website_slides/static/src/xml/website_slides.xml', qweb);

var SlideDialog = Widget.extend({
    template: 'website.slide.upload',
    events: {
        'hidden.bs.modal': 'destroy',
        'click button.save': 'save',
        'click button[data-dismiss="modal"]': 'cancel',
        'change input#upload': 'slide_upload',
        'change input#url': 'slide_url',
        'click .list-group-item': function (ev) {
            this.$('.list-group-item').removeClass('active');
            $(ev.target).closest('li').addClass('active');
        }
    },
    init: function (el, channel_id) {
        this._super(el, channel_id);
        this.channel_id = parseInt(channel_id, 10);
        this.file = {};
        this.index_content = "";
    },
    start: function () {
        this.$el.modal({
            backdrop: 'static'
        });
        this.set_category_id();
        this.set_tag_ids();
    },
    slide_url: function (ev) {
        var self = this,
            value = {
                'url': $(ev.target).val(),
                'channel_id': self.channel_id
            };
        this.$('.alert-warning').remove();
        this.is_valid_url = false;
        this.$('.save').button('loading');
        ajax.jsonRpc('/slides/dialog_preview/', 'call', value).then(function (data) {
            self.$('.save').button('reset');
            if (data.error) {
                self.display_alert(data.error);
            } else {
                self.$("#slide-image").attr("src", data.url_src);
                self.$('#name').val(data.title);
                self.$('#description').val(data.description);
                self.is_valid_url = true;
            }
        });
    },
    check_unique_slide: function (file_name) {
        var self = this;
        return ajax.jsonRpc('/web/dataset/call_kw', 'call', {
            model: 'slide.slide',
            method: 'search_count',
            args: [[['channel_id', '=', self.channel_id], ['name', '=', file_name]]],
            kwargs: {}
        });
    },
    slide_upload: function (ev) {
        var self = this,
            file = ev.target.files[0],
            is_image = /^image\/.*/.test(file.type),
            loaded = false;
        this.file.name = file.name;
        this.file.type = file.type;
        if (!(is_image || this.file.type === 'application/pdf')) {
            this.display_alert(_t("Invalid file type. Please select pdf or image file"));
            this.reset_file();
            return;
        }
        if (file.size / 1024 / 1024 > 15) {
            this.display_alert(_t("File is too big. File size cannot exceed 15MB"));
            this.reset_file();
            return;
        }
        this.$('.alert-warning').remove();
        var BinaryReader = new FileReader();
        // file read as DataURL
        BinaryReader.readAsDataURL(file);
        BinaryReader.onloadend = function (upload) {
            var buffer = upload.target.result;
            if (is_image) {
                self.$("#slide-image").attr("src", buffer);
            }
            buffer = buffer.split(',')[1];
            self.file.data = buffer;
        };

        if (file.type === 'application/pdf') {
            var ArrayReader = new FileReader();
            this.$('.save').button('loading');
            // file read as ArrayBuffer for PDFJS get_Document API
            ArrayReader.readAsArrayBuffer(file);
            ArrayReader.onload = function (evt) {
                var buffer = evt.target.result;
                var passwordNeeded = function () {
                    self.display_alert(_t("You can not upload password protected file."));
                    self.reset_file();
                    self.$('.save').button('reset');
                };
                PDFJS.getDocument(new Uint8Array(buffer), null, passwordNeeded).then(function getPdf(pdf) {
                    pdf.getPage(1).then(function getFirstPage(page) {
                        var scale = 1;
                        var viewport = page.getViewport(scale);
                        var canvas = document.getElementById('data_canvas');
                        var context = canvas.getContext('2d');
                        canvas.height = viewport.height;
                        canvas.width = viewport.width;
                        // Render PDF page into canvas context
                        page.render({
                            canvasContext: context,
                            viewport: viewport
                        }).then(function () {
                            var image_data = self.$('#data_canvas')[0].toDataURL();
                            self.$("#slide-image").attr("src", image_data);
                            if (loaded) {
                                self.$('.save').button('reset');
                            }
                            loaded = true;

                        });
                    });
                    var maxPages = pdf.pdfInfo.numPages;
                    var page, j;
                    self.index_content = "";
                    for (j = 1; j <= maxPages; j += 1) {
                        page = pdf.getPage(j);
                        page.then(function (page_obj) {
                            var page_number = page_obj.pageIndex + 1;
                            page_obj.getTextContent().then(function (data) {
                                var page_content = '';
                                _.each(data.items, function (obj) {
                                    page_content = page_content + obj.str + " ";
                                });
                                self.index_content = self.index_content + page_number + ". " + page_content + '\n';
                                if (maxPages === page_number) {
                                    if (loaded) {
                                        self.$('.save').button('reset');
                                    }
                                    loaded = true;
                                }
                            });
                        });
                    }
                });
            };
        }

        var input = file.name;
        var input_val = input.substr(0, input.lastIndexOf('.')) || input;
        this.check_unique_slide(input_val).then(function (exist) {
            if (exist) {
                var message = _t("Channel contains the given title, please change before Save or Publish.");
                self.display_alert(message);
            }
            self.$('#name').val(input_val);
        });
    },
    reset_file: function () {
        var control = this.$('#upload');
        control.replaceWith(control = control.clone(true));
        this.file.name = false;
    },
    display_alert: function (message) {
        this.$('.alert-warning').remove();
        $('<div class="alert alert-warning" role="alert">' + message + '</div>').insertBefore(this.$('form'));
    },

    /**
        Wrapper for select2 load data from server at once and store it.

        @param {String} Placeholder for element.
        @param {bool}  true for multiple selection box, false for single selection
        @param {Function} Function to fetch data from remote location should return $.deferred object
        resolved data should be array of object with id and name. eg. [{'id': id, 'name': 'text'}, ...]
        @returns {Object} select2 wrapper object
    */
    select2_wrapper: function (tag, multi, fetch_fnc) {
        return {
            width: '100%',
            placeholder: tag,
            allowClear: true,
            formatNoMatches: false,
            multiple: multi,
            selection_data: false,
            fetch_rpc_fnc : fetch_fnc,
            formatSelection: function (data) {
                if (data.tag) {
                    data.text = data.tag;
                }
                return data.text;
            },
            createSearchChoice: function(term, data) {
                var added_tags = $(this.opts.element).select2('data');
                if (_.filter(_.union(added_tags, data), function(tag) {
                    return tag.text.toLowerCase().localeCompare(term.toLowerCase()) === 0;
                }).length === 0) {
                    return {
                        id: _.uniqueId('tag_'),
                        create: true,
                        tag: term,
                        text: _.str.sprintf(_t("Create new tag '%s'"), term),
                    };
                }
            },
            fill_data: function (query, data) {
                var that = this,
                    tags = {results: []};
                _.each(data, function (obj) {
                    if (that.matcher(query.term, obj.name)) {
                        tags.results.push({id: obj.id, text: obj.name });
                    }
                });
                query.callback(tags);
            },
            query: function (query) {
                var that = this;
                // fetch data only once and store it
                if (!this.selection_data) {
                    this.fetch_rpc_fnc().then(function (data) {
                        that.fill_data(query, data);
                        that.selection_data = data;
                    });
                } else {
                    this.fill_data(query, this.selection_data);
                }
            }
        };
    },
    // Category management from select2
    set_category_id: function () {
        var self =  this;
        $('#category_id').select2(this.select2_wrapper(_t('Category'), false,
            function () {
                return ajax.jsonRpc("/web/dataset/call_kw", 'call', {
                    model: 'slide.category',
                    method: 'search_read',
                    args: [],
                    kwargs: {
                        fields: ['name'],
                        domain: [['channel_id', '=', self.channel_id]],
                        context: base.get_context()
                    }
                });
            }));
    },
    get_category_id: function () {
        var value = $('#category_id').select2('data');
        if (value && value.create) {
            return [0, {'name': value.text}];
        }
        return [value ? value.id : null];
    },
    // Tags management from select2
    set_tag_ids: function () {
        $('#tag_ids').select2(this.select2_wrapper(_t('Tags'), true, function () {
            return ajax.jsonRpc("/web/dataset/call_kw", 'call', {
                model: 'slide.tag',
                method: 'search_read',
                args: [],
                kwargs: {
                    fields: ['name'],
                    context: base.get_context()
                }
            });
        }));
    },
    get_tag_ids: function () {
        var res = [];
        _.each($('#tag_ids').select2('data'),
            function (val) {
                if (val.create) {
                    res.push([0, 0, {'name': val.text}]);
                } else {
                    res.push([4, val.id]);
                }
            });
        return res;
    },
    //Python PIL does not support SVG, so converting SVG to PNG
    svg_to_png: function() {
        var img = this.$el.find("img#slide-image")[0];
        var canvas = document.createElement("canvas");
        canvas.width = img.width;
        canvas.height = img.height;
        canvas.getContext("2d").drawImage(img, 0, 0);
        return canvas.toDataURL("image/png").split(',')[1];
    },
    // Values and save
    get_value: function () {
        var canvas = this.$('#data_canvas')[0],
            values = {
                'channel_id': this.channel_id || '',
                'name': this.$('#name').val(),
                'url': this.$('#url').val(),
                'description': this.$('#description').val(),
                'tag_ids': this.get_tag_ids(),
                'category_id': this.get_category_id()
            };
        if (this.file.type === 'application/pdf') {
            _.extend(values, {
                'image': canvas.toDataURL().split(',')[1],
                'index_content': this.index_content,
                'slide_type': canvas.height > canvas.width ? 'document' : 'presentation',
                'mime_type': this.file.type,
                'datas': this.file.data
            });
        }
        if (/^image\/.*/.test(this.file.type)) {
            _.extend(values, {
                'slide_type': 'infographic',
                'mime_type': this.file.type === 'image/svg+xml' ? 'image/png' : this.file.type,
                'datas': this.file.type === 'image/svg+xml' ? this.svg_to_png() : this.file.data
            });
        }
        return values;
    },
    validate: function () {
        this.$('.form-group').removeClass('has-error');
        if (!this.$('#name').val()) {
            this.$('#name').closest('.form-group').addClass('has-error');
            return false;
        }
        var url = this.$('#url').val() ? this.is_valid_url : false;
        if (!(this.file.name || url)) {
            this.$('#url').closest('.form-group').addClass('has-error');
            return false;
        }
        return true;
    },
    save: function (ev) {
        var self = this;
        if (this.validate()) {
            var values = this.get_value();
            if ($(ev.target).data('published')) {
                values.website_published = true;
            }
            this.$('.oe_slides_upload_loading').show();
            this.$('.modal-footer, .modal-body').hide();
            ajax.jsonRpc("/slides/add_slide", 'call', values).then(function (data) {
                if (data.error) {
                    self.display_alert(data.error);
                    self.$('.oe_slides_upload_loading').hide();
                    self.$('.modal-footer, .modal-body').show();

                } else {
                    window.location = data.url;
                }
            });
        }
    },
    cancel: function () {
        this.trigger("cancel");
    }
});

    // bind the event to the button
    $('.oe_slide_js_upload').on('click', function () {
        var channel_id = $(this).attr('channel_id');
        slides.page_widgets['upload_dialog'] = new SlideDialog(this, channel_id).appendTo(document.body);
    });

});
