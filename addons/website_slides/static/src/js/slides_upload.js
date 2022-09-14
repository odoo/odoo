/** @odoo-module **/

import { qweb as QWeb, _t } from 'web.core';
import Dialog from 'web.Dialog';
import publicWidget from 'web.public.widget';
import utils from 'web.utils';
import wUtils from 'website.utils';

var SlideUploadDialog = Dialog.extend({
    template: 'website.slide.upload.modal',
    events: _.extend({}, Dialog.prototype.events, {
        'click .o_wslides_js_upload_install_button': '_onClickInstallModule',
        'click .o_wslides_select_category': '_onClickSlideCategoryIcon',
        'change input#upload': '_onChangeSlideUpload',
        'change input#video_url': '_onChangeVideoUrl',
        'change input#image_google_url': '_onChangeImageUrl',
        'change input#document_google_url': '_onChangeDocumentUrl',
        'change input[name="source_type"]': '_onChangeSourceType',
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
            title: _t("Add Content"),
            size: 'medium',
        });
        this._super(parent, options);
        this._setup();

        this.channelID = parseInt(options.channelId, 10);
        this.defaultCategoryID = parseInt(options.categoryId, 10);
        this.canUpload = options.canUpload === 'True';
        this.canPublish = options.canPublish === 'True';
        this.modulesToInstall = options.modulesToInstall ? JSON.parse(options.modulesToInstall.replace(/'/g, '"')) : null;
        this.modulesToInstallStatus = null;

        if (options.openModal && options.openModal in this.slide_category_data) {
            // Sets the appropriate category's upload template if one has to be opened on load.
            this.set('state', options.openModal);
            this.set('defaultTemplate', this.slide_category_data[options.openModal]['template']);
        } else {
            this.set('state', '_select');
            this.set('defaultTemplate', 'website.slide.upload.modal.select');
        }
        this.on('change:state', this, this._onChangeType);
        this.set('can_submit_form', false);
        this.on('change:can_submit_form', this, this._onChangeCanSubmitForm);

        this.file = {};
        this.isValidUrl = true;
    },
    start: function () {
        var self = this;
        return this._super.apply(this, arguments).then(function () {
            if (self.get('state') !== '_select') {
                self.$modal.find('.modal-dialog').addClass('modal-lg');
            }
            self._bindSelect2Dropdown();
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
    _alertDisplay: function (message, alertClass='alert-warning') {
        this._alertRemove();
        $('<div/>', {
            "class": 'alert ' + alertClass,
            id: 'upload-alert',
            role: 'alert'
        }).text(message).insertBefore(this.$('form'));
    },
    _alertRemove: function () {
        this.$('#upload-alert').remove();
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
    _fetchUrlPreview: function (url, slideCategory) {
        return this._rpc({
            route: '/slides/prepare_preview/',
            params: {
                'url': url,
                'slide_category': slideCategory,
                'channel_id': this.channelID
            },
        });
    },
    _formSetFieldValue: function (fieldId, value) {
        var $formField = this.$('form').find('#'+fieldId);
        if (!$formField.val()) {  // update only if the user did not assign a value manually
            $formField.val(value);
        }
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
     * Extract values to submit from form, force the slide_category according to
     * filled values.
     *
     * @private
     */
    _formValidateGetValues: async function (forcePublished) {
        var slideCategory = 'document';
        // default slide_category (for article for instance)
        if (_.contains(this.slide_category_data), this.get('state')) {
            slideCategory = this.get('state');
        }

        var sourceType = 'local_file';
        if (slideCategory === 'video') {
            sourceType = 'external';  // force external for videos
        } else {
            sourceType = this.$('input[name="source_type"]:checked').data('value');
        }
        var values = _.extend({
            'channel_id': this.channelID,
            'description': this._formGetFieldValue('description'),
            'document_google_url': this._formGetFieldValue('document_google_url'),
            'duration': this._formGetFieldValue('duration'),
            'image_google_url': this._formGetFieldValue('image_google_url'),
            'is_published': forcePublished,
            'name': this._formGetFieldValue('name'),
            'slide_category': slideCategory,
            'source_type': sourceType,
            'video_url': this._formGetFieldValue('video_url'),
        }, this._getSelect2DropdownValues()); // add tags and category

        var canvas = this.$('#data_canvas')[0];
        if (this.file.type === 'application/pdf') {
            _.extend(values, {
                'image_1920': canvas.toDataURL().split(',')[1],
                'slide_category': 'document',
                'binary_content': this.file.data
            });
        } else if (values['slide_category'] === 'article') {
            _.extend(values, {
                'image_1920': this.file.type === 'image/svg+xml' ? await this._svgToPng() : this.file.data,
            });
        } else if (/^image\/.*/.test(this.file.type)) {
            _.extend(values, {
                'slide_category': 'infographic',
                'binary_content': this.file.type === 'image/svg+xml' ? await this._svgToPNG() : this.file.data,
            });
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
            btnList.push({text: _t("Back"), classes: 'o_w_slide_go_back', click: this._onClickGoBack.bind(this)});
        } else if (state !== '_upload') { // no button when uploading
            if (this.canUpload) {
                if (this.canPublish) {
                    btnList.push({text: _t("Save & Publish"), classes: 'btn-primary o_w_slide_upload o_w_slide_upload_published', click: this._onClickFormSubmit.bind(this)});
                    btnList.push({text: _t("Save"), classes: 'o_w_slide_upload', click: this._onClickFormSubmit.bind(this)});
                } else {
                    btnList.push({text: _t("Save"), classes: 'btn-primary o_w_slide_upload', click: this._onClickFormSubmit.bind(this)});
                }
            }
            btnList.push({text: _t("Back"), classes: 'o_w_slide_go_back', click: this._onClickGoBack.bind(this)});
        }
        return btnList;
    },
    /**
     * Get value for category_id and tag_ids (ORM cmd) to send to server
     *
     * @private
     */
    _getSelect2DropdownValues: function () {
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
        if (!self.defaultCategoryID) {
            var categoryValue = this.$('#category_id').select2('data');
            if (categoryValue && categoryValue.create) {
                result['category_id'] = [0, {'name': categoryValue.text}];
            } else if (categoryValue) {
                result['category_id'] = [categoryValue.id];
                this.categoryID = categoryValue.id;
            }
        } else {
            result['category_id'] = [self.defaultCategoryID];
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
                var self = this,
                    tags = {results: []};
                _.each(data, function (obj) {
                    if (self.matcher(query.term, obj[nameKey])) {
                        tags.results.push({id: obj.id, text: obj[nameKey]});
                    }
                });
                query.callback(tags);
            },
            query: function (query) {
                var self = this;
                // fetch data only once and store it
                if (!this.selection_data) {
                    this.fetch_rpc_fnc().then(function (data) {
                        self.can_create = data.can_create;
                        self.fill_data(query, data.read_results);
                        self.selection_data = data.read_results;
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
     * Init the data relative to the support slide category to upload
     *
     * @private
     */
    _setup: function () {
        this.slide_category_data = {
            document: {
                icon: 'fa-file-pdf-o',
                label: _t('Document'),
                template: 'website.slide.upload.modal.document',
            },
            infographic: {
                icon: 'fa-file-image-o',
                label: _t('Image'),
                template: 'website.slide.upload.modal.infographic',
            },
            article: {
                icon: 'fa-file-text',
                label: _t('Article'),
                template: 'website.slide.upload.modal.article',
            },
            video: {
                icon: 'fa-file-video-o',
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
     * Show the preview
     * @private
     */
    _showPreviewColumn: function () {
        this.$('.o_slide_tutorial').addClass('d-none');
        this.$('.o_slide_preview').removeClass('d-none');
    },
    /**
     * Hide the preview
     * @private
     */
    _hidePreviewColumn: function () {
        this.$('.o_slide_tutorial').removeClass('d-none');
        this.$('.o_slide_preview').addClass('d-none');
    },
    /**
     * TODO: Remove this part, as now SVG support in image resize tools is
     * included?
     * Python PIL does not support SVG, so converting SVG to PNG.
     *
     * @returns {Promise<string>}
     */
    _svgToPNG: async function () {
        const imgEl = this.$el.find('img#slide-image')[0];
        const png = await wUtils.svgToPNG(imgEl);
        return png.split(',')[1];
    },

    /**
     * When the URL changes for slides of categories infographic, document and video, we attempt to fetch
     * some metadata on YouTube / Google Drive (such as a name, a title, a duration, ...).
     *
     * @param {string} url
     * @param {string} slideCategory
     */
    _updateSlideMetadata: function (url, slideCategory) {
        var self = this;
        this._alertRemove();
        this.isValidUrl = false;
        this.set('can_submit_form', false);
        this._setModalLoading(true);
        this._fetchUrlPreview(url, slideCategory).then(function (data) {
            self.set('can_submit_form', true);
            if (data.error) {
                self._alertDisplay(data.error);
                self._hidePreviewColumn();
            } else {
                if (data.info) {
                    self._alertDisplay(data.info, 'alert-info');
                } else {
                    self._alertRemove();
                }

                self.isValidUrl = true;

                if (data.name) {
                    self._formSetFieldValue('name', data.name);
                    self.$('#slide-video-title')
                        .text(data.name)
                        .removeClass('d-none');
                } else {
                    self.$('#slide-video-title').addClass('d-none');
                }

                if (data.description) {
                    self._formSetFieldValue('description', data.description);
                }
                if (data.completion_time) {
                    // hours to minutes conversion
                    self._formSetFieldValue('duration', Math.round(data.completion_time * 60));
                }
                if (data.image_url) {
                    self.$('#slide-image').attr('src', data.image_url);
                }

                if (!data.name && !data.description && !data.image_url) {
                    self._hidePreviewColumn();
                } else {
                    self._showPreviewColumn();
                }
            }

            self._setModalLoading(false);
        });
    },

    /**
     * Typically used when loading slide metadata.
     * Since the request result will change form values, it's better to wait for the return of the
     * request to avoid having the user type text that will be overridden (such as the slide name
     * for example).
     *
     * @param {boolean} loading true to mask the modal with a loading screen, false to remove it
     */
    _setModalLoading: function (loading) {
        if (loading) {
            this.$el.closest('.modal-content').append(QWeb.render('website.slide.upload.modal.loading'));
        } else {
            this.$el.closest('.modal-content').find('.o_wslides_slide_upload_loading').remove();
        }
    },

    //--------------------------------------------------------------------------
    // Handler
    //--------------------------------------------------------------------------

    _onChangeType: function () {
        var currentType = this.get('state');
        var tmpl;
        this.$modal.find('.modal-dialog').removeClass('modal-lg');
        if (currentType === '_select') {
            tmpl = 'website.slide.upload.modal.select';
        } else if (currentType === '_upload') {
            tmpl = 'website.slide.upload.modal.uploading';
        } else if (currentType === '_import') {
            tmpl = 'website.slide.upload.modal.import';
        } else {
            tmpl = this.slide_category_data[currentType]['template'];
            this.$modal.find('.modal-dialog').addClass('modal-lg');
        }
        this.$('.o_w_slide_upload_modal_container').empty();
        this.$('.o_w_slide_upload_modal_container').append(QWeb.render(tmpl, {widget: this}));

        this._resetModalButton();

        if (currentType === '_import') {
            this.set_title(_t("New Certification"));
        } else {
            this.set_title(_t("Add Content"));
        }
    },
    _onChangeCanSubmitForm: function (ev) {
        if (this.get('can_submit_form')) {
            this.$('.o_w_slide_upload').button('reset');
        } else {
            this.$('.o_w_slide_upload').button('loading');
        }
    },
    /**
     * When the user selects 'local_file' or 'external' as source type, we display the 'upload'
     * field or the 'document_google_url' / 'image_google_url' fields respectively.
     * We also toggle the 'required' attribute the same way.
     *
     * @param {Event} ev the onchange event
     */
    _onChangeSourceType: function (ev) {
        if (this.$('#source_type_local_file').is(':checked')) {
            this.$('.o_wslides_js_slide_upload_local_file').removeClass('d-none');
            this.$('.o_wslides_js_slide_upload_external').addClass('d-none');

            this.$('#upload').attr('required', 'required');
            this.$('#document_google_url, #image_google_url').removeAttr('required');
        } else if (this.$('#source_type_external').is(':checked')) {
            this.$('.o_wslides_js_slide_upload_external').removeClass('d-none');
            this.$('.o_wslides_js_slide_upload_local_file').addClass('d-none');

            this.$('#document_google_url, #image_google_url').attr('required', 'required');
            this.$('#upload').removeAttr('required');
        }
    },
    _onChangeSlideUpload: function (ev) {
        var self = this;
        this._alertRemove();

        var $input = $(ev.currentTarget);
        var preventOnchange = $input.data('preventOnchange');
        var $preview = self.$('#slide-image');

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
                $preview.attr('src', buffer);
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
                window.Util = window.pdfjsLib.Util;
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
                            $preview.attr('src', imageData);
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
            if (this._formGetFieldValue('name') === "") {
                this._formSetFieldValue('name', inputVal);
            }
        }
    },
    _onChangeDocumentUrl: function (ev) {
        this._updateSlideMetadata($(ev.target).val(), 'document');
    },
    _onChangeImageUrl: function (ev) {
        this._updateSlideMetadata($(ev.target).val(), 'infographic');
    },
    _onChangeVideoUrl: function (ev) {
        this._updateSlideMetadata($(ev.target).val(), 'video');
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
            this.modulesToInstallStatus = _.extend({}, _.find(this.modulesToInstall, function (item) { return item.id === moduleId; }));
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
            let redirectUrl = window.location.origin + window.location.pathname + '?enable_slide_upload';
            if (self.modulesToInstallStatus.default_slide_category) {
                redirectUrl += '=';
                redirectUrl += self.modulesToInstallStatus.default_slide_category;
            }
            window.location.href = redirectUrl;
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
    /**
     * @private
     * @returns {Promise}
     */
    _onClickFormSubmit: async function (ev) {
        if (!this._formValidate()) {
            return;
        }

        // Get info before changing state
        const forcePublished = $(ev.currentTarget).hasClass('o_w_slide_upload_published');
        const values = await this._formValidateGetValues(forcePublished);

        var oldType = this.get('state');
        this.set('state', '_upload');

        const data = await this._rpc({
            route: '/slides/add_slide',
            params: values,
        });
        this._onFormSubmitDone(data, oldType);
    },

    _onFormSubmitDone: function (data, oldType) {
        if (data.error) {
            this.set('state', oldType);
            this._alertDisplay(data.error);
        } else {
            if (data.url.indexOf('enable_editor') >= 0) {
                // If we need to enter edit mode, it should be done to the top
                // window so that we endup refreshing the backend client action
                // in edit mode.
                window.top.location = data.url;
            } else {
                window.location = data.url;
            }
        }
    },

    _onClickSlideCategoryIcon: function (ev) {
        var $elem = this.$(ev.currentTarget);
        var slideCategory = $elem.data('slideCategory');
        this.set('state', slideCategory);

        this._bindSelect2Dropdown();  // rebind select2 at each modal body rendering
    },
});

publicWidget.registry.websiteSlidesUpload = publicWidget.Widget.extend({
    selector: '.o_wslides_js_slide_upload',
    events: {
        'click': '_onUploadClick',
    },

    /**
     * Automatically opens the upload dialog if requested from query string.
     * If openModal is defined ( === '' ), opens the category selection dialog.
     * If openModal is a category name, opens the category's upload dialog.
     *
     * @override
     */
    start: function () {
        if ('openModal' in this.$el.data()) {
            this._openDialog(this.$el);
            this.$el.data('openModal', false);
        }
        return this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    _openDialog: function ($element) {
        return new SlideUploadDialog(this, $element.data()).open();
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

export default {
    SlideUploadDialog: SlideUploadDialog,
    websiteSlidesUpload: publicWidget.registry.websiteSlidesUpload
};
