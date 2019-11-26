odoo.define('website_slides.upload_modal', function (require) {
'use strict';

var core = require('web.core');
var Dialog = require('web.Dialog');
var publicWidget = require('web.public.widget');
var utils = require('web.utils');

var QWeb = core.qweb;
var _t = core._t;

var SlideUploadDialog = Dialog.extend({
    template: 'website.slide.upload.modal',
    events: _.extend({}, Dialog.prototype.events, {
        'click .o_wslides_js_upload_install_button': '_onClickInstallModule',
        'click .o_wslides_select_type': '_onClickSlideTypeIcon',
        'change input#upload': '_onChangeSlideUpload',
        'change input#url': '_onChangeSlideUrl',
    }),

    /**
     * @override
     * @param {Object} parent
     * @param {Object} options holding channelId and optionally upload and publish control parameters
     * @param {Object} options.modulesToInstall: list of additional modules to
     *      install {id: module ID, name: module short description}
     */
    init: function (parent, options) {
        options = _.defaults(options || {}, {
            title: _t("Upload a document"),
            size: 'medium',
        });
        this._super(parent, options);
        this._setup();

        this.channelID = parseInt(options.channelId, 10);
        this.defaultCategoryID = parseInt(options.categoryId,10);
        this.canUpload = options.canUpload === 'True';
        this.canPublish = options.canPublish === 'True';
        this.modulesToInstall = options.modulesToInstall ? JSON.parse(options.modulesToInstall.replace(/'/g, '"')) : null;
        this.modulesToInstallStatus = null;

        this.set('state', '_select');
        this.on('change:state', this, this._onChangeType);
        this.set('can_submit_form', false);
        this.on('change:can_submit_form', this, this._onChangeCanSubmitForm);

        this.file = {};
        this.isValidUrl = true;
    },
    start: function () {
        var self = this;
        return this._super.apply(this, arguments).then(function () {
            self._resetModalButton();
        });
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {string} message
     */
    _alertDisplay: function (message) {
        this._alertRemove();
        $('<div/>', {
            "class": 'alert alert-warning',
            role: 'alert'
        }).text(message).insertBefore(this.$('form'));
    },
    _alertRemove: function () {
        this.$('.alert-warning').remove();
    },
    /**
     * Section and tags management from select2
     *
     * @private
     */
    _bindSelect2Dropdown: function () {
        var self = this;
        this.$('#category_id').select2(this._select2Wrapper(_t('Section'), false,
            function () {
                return self._rpc({
                    route: '/slides/category/search_read',
                    params: {
                        fields: ['name'],
                        domain: [['channel_id', '=', self.channelID]],
                    }
                });
            })
        );
        this.$('#tag_ids').select2(this._select2Wrapper(_t('Tags'), true, function () {
            return self._rpc({
                route: '/slides/tag/search_read',
                params: {
                    fields: ['name'],
                    domain: [],
                }
            });
        }));
    },
    _fetchUrlPreview: function (url) {
        return this._rpc({
            route: '/slides/prepare_preview/',
            params: {
                'url': url,
                'channel_id': this.channelID
            },
        });
    },
    _formSetFieldValue: function (fieldId, value) {
        this.$('form').find('#'+fieldId).val(value);
    },
    _formGetFieldValue: function (fieldId) {
        return this.$('#'+fieldId).val();
    },
    _formValidate: function () {
        var form = this.$("form");
        form.addClass('was-validated');
        return form[0].checkValidity() && this.isValidUrl;
    },
    /**
     * Extract values to submit from form, force the slide_type according to
     * filled values.
     *
     * @private
     */
    _formValidateGetValues: function (forcePublished) {
        var canvas = this.$('#data_canvas')[0];
        var values = _.extend({
            'channel_id': this.channelID,
            'name': this._formGetFieldValue('name'),
            'url': this._formGetFieldValue('url'),
            'description': this._formGetFieldValue('description'),
            'duration': this._formGetFieldValue('duration'),
            'is_published': forcePublished,
        }, this._getSelect2DropdownValues()); // add tags and category

        // default slide_type (for webpage for instance)
        if (_.contains(this.slide_type_data), this.get('state')) {
            values['slide_type'] = this.get('state');
        }

        if (this.file.type === 'application/pdf') {
            _.extend(values, {
                'image': canvas.toDataURL().split(',')[1],
                'slide_type': canvas.height > canvas.width ? 'document' : 'presentation',
                'mime_type': this.file.type,
                'datas': this.file.data
            });
        } else if (values['slide_type'] === 'webpage') {
            _.extend(values, {
                'mime_type': 'text/html',
                'image': this.file.type === 'image/svg+xml' ? this._svgToPng() : this.file.data,
            });
        } else if (/^image\/.*/.test(this.file.type)) {
            if (values['slide_type'] === 'presentation') {
                _.extend(values, {
                    'slide_type': 'infographic',
                    'mime_type': this.file.type === 'image/svg+xml' ? 'image/png' : this.file.type,
                    'datas': this.file.type === 'image/svg+xml' ? this._svgToPng() : this.file.data
                });
            } else {
                _.extend(values, {
                    'image': this.file.type === 'image/svg+xml' ? this._svgToPng() : this.file.data,
                });
            }
        }
        return values;
    },
    /**
     * @private
     */
    _fileReset: function () {
        var control = this.$('#upload');
        control.replaceWith(control = control.clone(true));
        this.file.name = false;
    },

    _getModalButtons: function () {
        var btnList = [];
        var state = this.get('state');
        if (state === '_select') {
            btnList.push({text: _t("Cancel"), classes: 'o_w_slide_cancel', close: true});
        } else if (state === '_import') {
            if (! this.modulesToInstallStatus.installing) {
                btnList.push({text: this.modulesToInstallStatus.failed ? _t("Retry") : _t("Install"), classes: 'btn-primary', click: this._onClickInstallModuleConfirm.bind(this)});
            }
            btnList.push({text: _t("Go Back"), classes: 'o_w_slide_go_back', click: this._onClickGoBack.bind(this)});
        } else if (state !== '_upload') { // no button when uploading
            if (this.canUpload) {
                if (this.canPublish) {
                    btnList.push({text: _t("Publish"), classes: 'btn-primary o_w_slide_upload o_w_slide_upload_published', click: this._onClickFormSubmit.bind(this)});
                    btnList.push({text: _t("Save as Draft"), classes: 'o_w_slide_upload', click: this._onClickFormSubmit.bind(this)});
                } else {
                    btnList.push({text: _t("Save as Draft"), classes: 'btn-primary o_w_slide_upload', click: this._onClickFormSubmit.bind(this)});
                }
            }
            btnList.push({text: _t("Go Back"), classes: 'o_w_slide_go_back', click: this._onClickGoBack.bind(this)});
        }
        return btnList;
    },
    /**
     * Get value for category_id and tag_ids (ORM cmd) to send to server
     *
     * @private
     */
    _getSelect2DropdownValues: function (){
        var result = {};
        var self = this;
        // tags
        var tagValues = [];
        _.each(this.$('#tag_ids').select2('data'), function (val) {
            if (val.create) {
                tagValues.push([0, 0, {'name': val.text}]);
            } else {
                tagValues.push([4, val.id]);
            }
        });
        if (tagValues) {
            result['tag_ids'] = tagValues;
        }
        // category
        if (!self.defaultCategoryID){
            var categoryValue = this.$('#category_id').select2('data');
            if (categoryValue && categoryValue.create) {
                result['category_id'] = [0, {'name': categoryValue.text}];
            } else if (categoryValue) {
                result['category_id'] =  [categoryValue.id];
                this.categoryID = categoryValue.id;
            }
        } else {
            result['category_id'] =  [self.defaultCategoryID];
            this.categoryID = self.defaultCategoryID;
        }
        return result;
    },
    /**
     * Reset the footer buttons, according to current state of modal
     *
     * @private
     */
    _resetModalButton: function () {
        this.set_buttons(this._getModalButtons());
    },
    /**
     * Wrapper for select2 load data from server at once and store it.
     *
     * @private
     * @param {String} Placeholder for element.
     * @param {bool}  true for multiple selection box, false for single selection
     * @param {Function} Function to fetch data from remote location should return a Promise
     * resolved data should be array of object with id and name. eg. [{'id': id, 'name': 'text'}, ...]
     * @param {String} [nameKey='name'] (optional) the name key of the returned record
     *   ('name' if not provided)
     * @returns {Object} select2 wrapper object
    */
    _select2Wrapper: function (tag, multi, fetchFNC, nameKey) {
        nameKey = nameKey || 'name';

        var values = {
            width: '100%',
            placeholder: tag,
            allowClear: true,
            formatNoMatches: false,
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
                    if (this.opts.can_create) {
                        return {
                            id: _.uniqueId('tag_'),
                            create: true,
                            tag: term,
                            text: _.str.sprintf(_t("Create new %s '%s'"), tag, term),
                        };
                    } else {
                        return undefined;
                    }
                }
            },
            fill_data: function (query, data) {
                var that = this,
                    tags = {results: []};
                _.each(data, function (obj) {
                    if (that.matcher(query.term, obj[nameKey])) {
                        tags.results.push({id: obj.id, text: obj[nameKey]});
                    }
                });
                query.callback(tags);
            },
            query: function (query) {
                var that = this;
                // fetch data only once and store it
                if (!this.selection_data) {
                    this.fetch_rpc_fnc().then(function (data) {
                        that.can_create = data.can_create;
                        that.fill_data(query, data.read_results);
                        that.selection_data = data.read_results;
                    });
                } else {
                    this.fill_data(query, this.selection_data);
                }
            }
        };

        if (multi) {
            values['multiple'] = true;
        }

        return values;
    },
    /**
     * Init the data relative to the support slide type to upload
     *
     * @private
     */
    _setup: function () {
        this.slide_type_data = {
            presentation: {
                icon: 'fa-file-pdf-o',
                label: _t('Presentation'),
                template: 'website.slide.upload.modal.presentation',
            },
            webpage: {
                icon: 'fa-file-text',
                label: _t('Web Page'),
                template: 'website.slide.upload.modal.webpage',
            },
            video: {
                icon: 'fa-video-camera',
                label: _t('Video'),
                template: 'website.slide.upload.modal.video',
            },
            quiz: {
                icon: 'fa-question-circle',
                label: _t('Quiz'),
                template: 'website.slide.upload.quiz'
            }
        };
    },
    /**
     * Show the preview/right column and resize the modal
     * @private
     */
    _showPreviewColumn: function() {
        this.$('#o_wslides_js_slide_upload_left_column').removeClass('col').addClass('col-md-6');
        this.$('#o_wslides_js_slide_upload_preview_column').removeClass('d-none');
        this.$modal.find('.modal-dialog').addClass('modal-lg');
    },
    /**
     * Hide the preview/right column and resize the modal
     * @private
     */
    _hidePreviewColumn: function () {
        this.$('#o_wslides_js_slide_upload_left_column').addClass('col').removeClass('col-md-6');
        this.$('#o_wslides_js_slide_upload_preview_column').addClass('d-none');
        this.$modal.find('.modal-dialog').removeClass('modal-lg');
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
    //--------------------------------------------------------------------------
    // Handler
    //--------------------------------------------------------------------------

    _onChangeType: function () {
        var currentType = this.get('state');
        var tmpl;
        if (currentType === '_select') {
            tmpl = 'website.slide.upload.modal.select';
        } else if (currentType === '_upload') {
            tmpl = 'website.slide.upload.modal.uploading';
        } else if (currentType === '_import') {
            tmpl = 'website.slide.upload.modal.import';
        } else {
            tmpl = this.slide_type_data[currentType]['template'];
        }
        this.$('.o_w_slide_upload_modal_container').empty();
        this.$('.o_w_slide_upload_modal_container').append(QWeb.render(tmpl, {widget: this}));

        this._resetModalButton();

        if (currentType === '_import') {
            this.set_title(_t("New Certification"));
        } else {
            this.set_title(_t("Upload a document"));
        }

        this.$modal.find('.modal-dialog').removeClass('modal-lg');
    },
    _onChangeCanSubmitForm: function (ev) {
        if (this.get('can_submit_form')) {
            this.$('.o_w_slide_upload').button('reset');
        } else {
            this.$('.o_w_slide_upload').button('loading');
        }
    },
    _onChangeSlideUpload: function (ev) {
        var self = this;
        this._alertRemove();

        var $input = $(ev.currentTarget);
        var preventOnchange = $input.data('preventOnchange');

        var file = ev.target.files[0];
        if (!file) {
            this.$('#slide-image').attr('src', '/website_slides/static/src/img/document.png');
            this._hidePreviewColumn();
            return;
        }
        var isImage = /^image\/.*/.test(file.type);
        var loaded = false;
        this.file.name = file.name;
        this.file.type = file.type;
        if (!(isImage || this.file.type === 'application/pdf')) {
            this._alertDisplay(_t("Invalid file type. Please select pdf or image file"));
            this._fileReset();
            this._hidePreviewColumn();
            return;
        }
        if (file.size / 1024 / 1024 > 25) {
            this._alertDisplay(_t("File is too big. File size cannot exceed 25MB"));
            this._fileReset();
            this._hidePreviewColumn();
            return;
        }

        utils.getDataURLFromFile(file).then(function (buffer) {
            if (isImage) {
                self.$('#slide-image').attr('src', buffer);
            }
            buffer = buffer.split(',')[1];
            self.file.data = buffer;
            self._showPreviewColumn();
        });

        if (file.type === 'application/pdf') {
            var ArrayReader = new FileReader();
            this.set('can_submit_form', false);
            // file read as ArrayBuffer for pdfjsLib get_Document API
            ArrayReader.readAsArrayBuffer(file);
            ArrayReader.onload = function (evt) {
                var buffer = evt.target.result;
                var passwordNeeded = function () {
                    self._alertDisplay(_t("You can not upload password protected file."));
                    self._fileReset();
                    self.set('can_submit_form', true);
                };
                /**
                 * The following line fixes pdfjsLib 'Util' global variable.
                 * This is (most likely) related to #32181 which lazy loads most assets.
                 *
                 * That caused an issue where the global 'Util' variable from pdfjsLib can be
                 * (depending of which libraries load first) overridden by the global 'Util'
                 * variable of bootstrap.
                 * (See 'lib/bootstrap/js/util.js' and 'web/static/lib/pdfjs/build/pdfjs.js')
                 *
                 * This commit ensures that the global 'Util' variable is set to the one of pdfjsLib
                 * right before it's used.
                 *
                 * Eventually, we should update or get rid of one of the two libraries since they're
                 * not compatible together, or make a wrapper that makes them compatible.
                 * In the mean time, this small fix allows not refactoring all of this and can not
                 * cause much harm.
                 */
                Util = window.pdfjsLib.Util;
                window.pdfjsLib.getDocument(new Uint8Array(buffer), null, passwordNeeded).then(function getPdf(pdf) {
                    self._formSetFieldValue('duration', (pdf._pdfInfo.numPages || 0) * 5);
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
                                self.set('can_submit_form', true);
                            }
                            loaded = true;
                            self._showPreviewColumn();
                        });
                    });
                });
            };
        }

        if (!preventOnchange) {
            var input = file.name;
            var inputVal = input.substr(0, input.lastIndexOf('.')) || input;
            this._formSetFieldValue('name', inputVal);
        }
    },
    _onChangeSlideUrl: function (ev) {
        var self = this;
        var url = $(ev.target).val();
        this._alertRemove();
        this.isValidUrl = false;
        this.set('can_submit_form', false);
        this._fetchUrlPreview(url).then(function (data) {
            self.set('can_submit_form', true);
            if (data.error) {
                self._alertDisplay(data.error);
            } else {
                if (data.completion_time) {
                    // hours to minutes conversion
                    self._formSetFieldValue('duration', Math.round(data.completion_time * 60));
                }
                self.$('#slide-image').attr('src', data.url_src);
                self._formSetFieldValue('name', data.title);
                self._formSetFieldValue('description', data.description);

                self.isValidUrl = true;
                self._showPreviewColumn();
            }
        });
    },

    _onClickInstallModule: function (ev) {
        var $btn = $(ev.currentTarget);
        var moduleId = $btn.data('moduleId');
        if (this.modulesToInstallStatus) {
            this.set('state', '_import');
            if (this.modulesToInstallStatus.installing) {
                this.$('#o_wslides_install_module_text')
                    .text(_.str.sprintf(_t('Already installing "%s".'), this.modulesToInstallStatus.name));
            } else if (this.modulesToInstallStatus.failed) {
                this.$('#o_wslides_install_module_text')
                    .text(_.str.sprintf(_t('Failed to install "%s".'), this.modulesToInstallStatus.name));
            }
        } else {
            this.modulesToInstallStatus = _.extend({}, _.find(this.modulesToInstall, function (item) { return item.id == moduleId; }));
            this.set('state', '_import');
            this.$('#o_wslides_install_module_text')
                .text(_.str.sprintf(_t('Do you want to install the "%s" app?'), this.modulesToInstallStatus.name));
        }
    },

    _onClickInstallModuleConfirm: function () {
        var self = this;
        var $el = this.$('#o_wslides_install_module_text');
        $el.text(_.str.sprintf(_t('Installing "%s".'), this.modulesToInstallStatus.name));
        this.modulesToInstallStatus.installing = true;
        this._resetModalButton();
        this._rpc({
            model: 'ir.module.module',
            method: 'button_immediate_install',
            args: [[this.modulesToInstallStatus.id]],
        }).then(function () {
            window.location.href = window.location.origin + window.location.pathname + '?enable_slide_upload';
        }, function () {
            $el.text(_.str.sprintf(_t('Failed to install "%s".'), self.modulesToInstallStatus.name));
            self.modulesToInstallStatus.installing = false;
            self.modulesToInstallStatus.failed = true;
            self._resetModalButton();
        });
    },

    _onClickGoBack: function () {
        this.set('state', '_select');
        this.isValidUrl = true;
        if (this.modulesToInstallStatus && !this.modulesToInstallStatus.installing) {
            this.modulesToInstallStatus = null;
        }
    },
    _onClickFormSubmit: function (ev) {
        var self = this;
        var $btn = $(ev.currentTarget);
        if (this._formValidate()) {
            var values = this._formValidateGetValues($btn.hasClass('o_w_slide_upload_published')); // get info before changing state
            var oldType = this.get('state');
            this.set('state', '_upload');
            return this._rpc({
                route: '/slides/add_slide',
                params: values,
            }).then(function (data) {
                if (data.error) {
                    self.set('state', oldType);
                    self._alertDisplay(data.error);
                } else {
                    window.location = data.url;
                }
            });
        }
    },
    _onClickSlideTypeIcon: function (ev) {
        var $elem = this.$(ev.currentTarget);
        var slideType = $elem.data('slideType');
        this.set('state', slideType);

        this._bindSelect2Dropdown();  // rebind select2 at each modal body rendering
    },
});

publicWidget.registry.websiteSlidesUpload = publicWidget.Widget.extend({
    selector: '.o_wslides_js_slide_upload',
    xmlDependencies: ['/website_slides/static/src/xml/website_slides_upload.xml'],
    events: {
        'click': '_onUploadClick',
    },

    /**
     * @override
     */
    start: function () {
        // Automatically open the upload dialog if requested from query string
        if (this.$el.attr('data-open-modal')) {
            this.$el.removeAttr('data-open-modal');
            this._openDialog(this.$el);
        }
        return this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    _openDialog: function ($element) {
        var data = $element.data();
        return new SlideUploadDialog(this, data).open();
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {Event} ev
     */
    _onUploadClick: function (ev) {
        ev.preventDefault();
        this._openDialog($(ev.currentTarget));
    },
});

return {
    SlideUploadDialog: SlideUploadDialog,
    websiteSlidesUpload: publicWidget.registry.websiteSlidesUpload
};

});
