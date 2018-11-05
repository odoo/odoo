odoo.define('website_slides.upload', function (require) {
'use strict';

var sAnimations = require('website.content.snippets.animation');
var core = require('web.core');
var Widget = require('web.Widget');

var _t = core._t;

var SlideDialog = Widget.extend({
    template: 'website.slide.upload',
    events: {
        'hidden.bs.modal': 'destroy',
        'click button.save': '_save',
        'click button[data-dismiss="modal"]': '_cancel',
        'change input#upload': '_slideUpload',
        'change input#url': '_slideUrl',
        'click .list-group-item': function (ev) {
            this.$('.list-group-item').removeClass('active');
            $(ev.target).closest('li').addClass('active');
        }
    },

    /**
     * @override
     * @param {Object} el
     * @param {number} channel_id
     */
    init: function (el, channelID) {
        this._super(el, channelID);
        this.channel_id = parseInt(channelID, 10);
        this.file = {};
        this.index_content = '';
    },
    /**
     * @override
     */
    start: function () {
        this.$el.modal({
            backdrop: 'static'
        });
        this._setCategoryId();
        this._setTagIds();
        return this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {string} file_name
     */
    _checkUniqueSlide: function (fileName) {
        var self = this;
        return this._rpc({
            model: 'slide.slide',
            method: 'search_count',
            args: [[['channel_id', '=', self.channel_id], ['name', '=', fileName]]],
        });
    },
    /**
     * @private
     */
    _resetFile: function () {
        var control = this.$('#upload');
        control.replaceWith(control = control.clone(true));
        this.file.name = false;
    },
    /**
     * @private
     * @param {string} message
     */
    _displayAlert: function (message) {
        this.$('.alert-warning').remove();
        $('<div class="alert alert-warning" role="alert">' + message + '</div>').insertBefore(this.$('form'));
    },

    /**
     * Wrapper for select2 load data from server at once and store it.
     *
     * @private
     * @param {String} Placeholder for element.
     * @param {bool}  true for multiple selection box, false for single selection
     * @param {Function} Function to fetch data from remote location should return $.deferred object
     * resolved data should be array of object with id and name. eg. [{'id': id, 'name': 'text'}, ...]
     * @returns {Object} select2 wrapper object
    */
    _select2Wrapper: function (tag, multi, fetchFNC) {
        return {
            width: '100%',
            placeholder: tag,
            allowClear: true,
            formatNoMatches: false,
            multiple: multi,
            selection_data: false,
            fetch_rpc_fnc: fetchFNC,
            formatSelection: function (data) {
                if (data.tag) {
                    data.text = data.tag;
                }
                return data.text;
            },
            createSearchChoice: function (term, data) {
                var addedTags = $(this.opts.element).select2('data');
                if (_.filter(_.union(addedTags, data), function (tag) {
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
                        tags.results.push({id: obj.id, text: obj.name});
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
    /**
     * Category management from select2
     *
     * @private
     */
    _setCategoryId: function () {
        var self = this;
        $('#category_id').select2(this._select2Wrapper(_t('Category'), false,
            function () {
                return this._rpc({
                    model: 'slide.category',
                    method: 'search_read',
                    args: [],
                    kwargs: {
                        fields: ['name'],
                        domain: [['channel_id', '=', self.channel_id]],
                    }
                });
            }));
    },
    /**
     * @private
     */
    _getCategoryId: function () {
        var value = $('#category_id').select2('data');
        if (value && value.create) {
            return [0, {'name': value.text}];
        }
        return [value ? value.id : null];
    },
    /**
     * Tags management from select2
     *
     * @private
     */
    _setTagIds: function () {
        $('#tag_ids').select2(this._select2Wrapper(_t('Tags'), true, function () {
            return this._rpc({
                model: 'slide.tag',
                method: 'search_read',
                args: [],
                kwargs: {
                    fields: ['name'],
                }
            });
        }));
    },
    /**
     * @private
     */
    _getTagIds: function () {
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
    /**
     * @private
     */
    // TODO: Remove this part, as now SVG support in image resize tools is included
    //Python PIL does not support SVG, so converting SVG to PNG
    _svgToPng: function () {
        var img = this.$el.find('img#slide-image')[0];
        var canvas = document.createElement('canvas');
        canvas.width = img.width;
        canvas.height = img.height;
        canvas.getContext('2d').drawImage(img, 0, 0);
        return canvas.toDataURL('image/png').split(',')[1];
    },
    /**
     * Values and save
     *
     * @private
     */
    _getValue: function () {
        var canvas = this.$('#data_canvas')[0],
            values = {
                'channel_id': this.channel_id || '',
                'name': this.$('#name').val(),
                'url': this.$('#url').val(),
                'description': this.$('#description').val(),
                'tag_ids': this._getTagIds(),
                'category_id': this._getCategoryId()
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
                'datas': this.file.type === 'image/svg+xml' ? this._svgToPng() : this.file.data
            });
        }
        return values;
    },
    /**
     * @private
     */
    _validate: function () {
        this.$('.form-group').removeClass('o_has_error').find('.form-control, .custom-select').removeClass('is-invalid');
        if (!this.$('#name').val()) {
            this.$('#name').closest('.form-group').addClass('o_has_error').find('.form-control, .custom-select').addClass('is-invalid');
            return false;
        }
        var url = this.$('#url').val() ? this.is_valid_url : false;
        if (!(this.file.name || url)) {
            this.$('#url').closest('.form-group').addClass('o_has_error').find('.form-control, .custom-select').addClass('is-invalid');
            return false;
        }
        return true;
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @override
     * @param {Object} ev
     */
    _save: function (ev) {
        var self = this;
        if (this._validate()) {
            var values = this._getValue();
            if ($(ev.target).data('published')) {
                values.website_published = true;
            }
            this.$('.oe_slides_upload_loading').show();
            this.$('.modal-footer, .modal-body').hide();
            this._rpc({
                route: '/slides/add_slide',
                params: values,
            }).then(function (data) {
                if (data.error) {
                    self._displayAlert(data.error);
                    self.$('.oe_slides_upload_loading').hide();
                    self.$('.modal-footer, .modal-body').show();

                } else {
                    window.location = data.url;
                }
            });
        }
    },
    /**
     * @override
     */
    _cancel: function () {
        this.trigger('cancel');
    },
    /**
     * @override
     * @param {Object} ev
     */
    _slideUpload: function (ev) {
        var self = this;
        var file = ev.target.files[0];
        var isImage = /^image\/.*/.test(file.type);
        var loaded = false;
        this.file.name = file.name;
        this.file.type = file.type;
        if (!(isImage || this.file.type === 'application/pdf')) {
            this._displayAlert(_t("Invalid file type. Please select pdf or image file"));
            this._resetFile();
            return;
        }
        if (file.size / 1024 / 1024 > 25) {
            this._displayAlert(_t("File is too big. File size cannot exceed 25MB"));
            this._resetFile();
            return;
        }
        this.$('.alert-warning').remove();
        var BinaryReader = new FileReader();
        // file read as DataURL
        BinaryReader.readAsDataURL(file);
        BinaryReader.onloadend = function (upload) {
            var buffer = upload.target.result;
            if (isImage) {
                self.$('#slide-image').attr('src', buffer);
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
                    self._displayAlert(_t("You can not upload password protected file."));
                    self._resetFile();
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
                            var imageData = self.$('#data_canvas')[0].toDataURL();
                            self.$('#slide-image').attr('src', imageData);
                            if (loaded) {
                                self.$('.save').button('reset');
                            }
                            loaded = true;

                        });
                    });
                    var maxPages = pdf.pdfInfo.numPages;
                    var page, j;
                    self.index_content = '';
                    for (j = 1; j <= maxPages; j += 1) {
                        page = pdf.getPage(j);
                        page.then(function (pageObj) {
                            var pageNumber = pageObj.pageIndex + 1;
                            pageObj.getTextContent().then(function (data) {
                                var pageContent = '';
                                _.each(data.items, function (obj) {
                                    pageContent = pageContent + obj.str + ' ';
                                });
                                // page_content may contain null characters
                                pageContent = pageContent.replace(/\0/g, '');
                                self.index_content = self.index_content + pageNumber + '. ' + pageContent + '\n';
                                if (maxPages === pageNumber) {
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
        var inputVal = input.substr(0, input.lastIndexOf('.')) || input;
        this._checkUniqueSlide(inputVal).then(function (exist) {
            if (exist) {
                var message = _t("Channel contains the given title, please change before Save or Publish.");
                self._displayAlert(message);
            }
            self.$('#name').val(inputVal);
        });
    },
    /**
     * @private
     * @param {Object} ev
     */
    _slideUrl: function (ev) {
        var self = this,
            value = {
                'url': $(ev.target).val(),
                'channel_id': self.channel_id
            };
        this.$('.alert-warning').remove();
        this.is_valid_url = false;
        this.$('.save').button('loading');
        this._rpc({
            route: '/slides/dialog_preview/',
            params: value,
        }).then(function (data) {
            self.$('.save').button('reset');
            if (data.error) {
                self._displayAlert(data.error);
            } else {
                self.$('#slide-image').attr('src', data.url_src);
                self.$('#name').val(data.title);
                self.$('#description').val(data.description);
                self.is_valid_url = true;
            }
        });
    },

});

sAnimations.registry.websiteSlidesUpload = sAnimations.Class.extend({
    selector: '.oe_slide_js_upload',
    xmlDependencies: ['/website_slides/static/src/xml/website_slides.xml'],
    read_events: {
        'click': '_onUploadClick',
    },

    /**
     * @override
     */
    start: function () {
        // Automatically open the upload dialog if requested from query string
        if ($.deparam.querystring().enable_slide_upload !== undefined) {
            this._openDialog(this.$el.attr('channel_id'));
        }
        return this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    _openDialog: function (channelID) {
        new SlideDialog(this, channelID).appendTo(document.body);
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {Event} ev
     */
    _onUploadClick: function (ev) {
        this._openDialog($(ev.currentTarget).attr('channel_id'));
    },
});
});
