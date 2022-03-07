odoo.define('web_editor.field.html', function (require) {
'use strict';

var ajax = require('web.ajax');
var basic_fields = require('web.basic_fields');
var core = require('web.core');
var wysiwygLoader = require('web_editor.loader');
var field_registry = require('web.field_registry');
const {QWebPlugin} = require('@web_editor/js/backend/QWebPlugin');
// must wait for web/ to add the default html widget, otherwise it would override the web_editor one
require('web._field_registry');

var _lt = core._lt;
var TranslatableFieldMixin = basic_fields.TranslatableFieldMixin;
var QWeb = core.qweb;

/**
 * FieldHtml Widget
 * Intended to display HTML content. This widget uses the wysiwyg editor
 * improved by odoo.
 *
 * nodeOptions:
 *  - style-inline => convert class to inline style (no re-edition) => for sending by email
 *  - no-attachment
 *  - cssEdit
 *  - cssReadonly
 *  - snippets
 *  - wrapper
 *  - resizable
 *  - codeview
 */
var FieldHtml = basic_fields.DebouncedField.extend(TranslatableFieldMixin, {
    description: _lt("Html"),
    className: 'oe_form_field oe_form_field_html',
    supportedFieldTypes: ['html'],
    isQuickEditable: true,
    quickEditExclusion: [
        '[href]',
    ],

    custom_events: {
        wysiwyg_focus: '_onWysiwygFocus',
        wysiwyg_blur: '_onWysiwygBlur',
        wysiwyg_change: '_onChange',
        wysiwyg_attachment: '_onAttachmentChange',
    },

    /**
     * @override
     */
    willStart: async function () {
        this.isRendered = false;
        this._onUpdateIframeId = 'onLoad_' + _.uniqueId('FieldHtml');
        await this._super();
        if (this.nodeOptions.cssReadonly) {
            this.cssReadonly = await ajax.loadAsset(this.nodeOptions.cssReadonly);
        }
        if (this.nodeOptions.cssEdit || this.nodeOptions['style-inline']) {
            this.cssEdit = await ajax.loadAsset(this.nodeOptions.cssEdit || 'web_editor.assets_edit_html_field');
        }
    },
    /**
     * @override
     */
    destroy: function () {
        delete window.top[this._onUpdateIframeId];
        if (this.$iframe) {
            this.$iframe.remove();
        }
        if (this._qwebPlugin) {
            this._qwebPlugin.destroy();
        }
        this._super();
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    activate: function (options) {
        if (this.wysiwyg) {
            this.wysiwyg.focus();
            return true;
        }
    },
    /**
     * Wysiwyg doesn't notify for changes done in code mode. We override
     * commitChanges to manually switch back to normal mode before committing
     * changes, so that the widget is aware of the changes done in code mode.
     *
     * @override
     */
    commitChanges: function () {
        if (this.mode == "readonly" || !this.isRendered) {
            return this._super();
        }
        var _super = this._super.bind(this);
        this.wysiwyg.odooEditor.clean();
        return this.wysiwyg.saveModifiedImages(this.$content).then(() => {
            this._isDirty = this.wysiwyg.isDirty();
            _super();
        });
    },
    /**
     * @override
     */
    isSet: function () {
        var value = this.value && this.value.split('&nbsp;').join('').replace(/\s/g, ''); // Removing spaces & html spaces
        return value && value !== "<p></p>" && value !== "<p><br></p>" && value.match(/\S/);
    },
    /**
     * @override
     */
    getFocusableElement: function () {
        return this.wysiwyg && this.wysiwyg.$editable || $();
    },
    /**
     * Do not re-render this field if it was the origin of the onchange call.
     *
     * @override
     */
    reset: function (record, event) {
        this._reset(record, event);
        var value = this.value;
        if (this.nodeOptions.wrapper) {
            value = this._wrap(value);
        }
        value = this._textToHtml(value);
        if (!event || event.target !== this) {
            if (this.mode === 'edit' && this.wysiwyg) {
                this.wysiwyg.setValue(value);
            } else if (this.cssReadonly) {
                return Promise.resolve();
            } else {
                this.$content.html(value);
            }
        }
        return Promise.resolve();
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _getValue: function () {
        let value;
        if (!this._$codeview || this._$codeview.hasClass('d-none')) {
           value = this.wysiwyg.getValue();
        } else {
            value = this._$codeview.val();
        }
        if (this.nodeOptions.wrapper) {
            return this._unWrap(value);
        }
        return value;
    },
    /**
     * Create the wysiwyg instance with the target (this.$target)
     * then add the editable content (this.$content).
     *
     * @private
     * @returns {$.Promise}
     */
    _createWysiwygIntance: async function () {
        this.wysiwyg = await wysiwygLoader.createWysiwyg(this, this._getWysiwygOptions());
        return this.wysiwyg.appendTo(this.$el).then(() => {
            this.$content = this.wysiwyg.$editable;
            this._onLoadWysiwyg();
            this.isRendered = true;
        });
    },
    /**
     * Get wysiwyg options to create wysiwyg instance.
     *
     * @private
     * @returns {Object}
     */
    _getWysiwygOptions: function () {
        return Object.assign({}, this.nodeOptions, {
            recordInfo: {
                context: this.record.getContext(this.recordParams),
                res_model: this.model,
                res_id: this.res_id,
            },
            placeholder: this.attrs && this.attrs.placeholder,
            collaborationChannel: !!this.nodeOptions.collaborative && {
                collaborationModelName: this.model,
                collaborationFieldName: this.name,
                collaborationResId: parseInt(this.res_id),
            },
            noAttachment: this.nodeOptions['no-attachment'],
            inIframe: !!this.nodeOptions.cssEdit,
            iframeCssAssets: this.nodeOptions.cssEdit,
            snippets: this.nodeOptions.snippets,
            value: this.value,
            mediaModalParams: {
                noVideos: 'noVideos' in this.nodeOptions ? this.nodeOptions.noVideos : true,
            },
            linkForceNewWindow: true,
            tabsize: 0,
            height: this.nodeOptions.height,
            minHeight: this.nodeOptions.minHeight,
            maxHeight: this.nodeOptions.maxHeight,
            resizable: 'resizable' in this.nodeOptions ? this.nodeOptions.resizable : false,
            editorPlugins: [QWebPlugin],
        });
    },
    /**
     * Toggle the code view and update the UI.
     *
     * @param {JQuery} $codeview
     */
    _toggleCodeView: function ($codeview) {
        this.wysiwyg.odooEditor.observerUnactive();
        $codeview.height(this.$content.height());
        $codeview.toggleClass('d-none');
        this.$content.toggleClass('d-none');
        if ($codeview.hasClass('d-none')) {
            if (this.resizerHandleObserver) {
                this.resizerHandleObserver.disconnect();
                delete this.resizerHandleObserver;
            }
            this.wysiwyg.odooEditor.observerActive();
            this.wysiwyg.setValue($codeview.val());
        } else {
            this.resizerHandleObserver = new MutationObserver((mutations, observer) => {
                for (let mutation of mutations) {
                    if (mutation.type === 'attributes' && mutation.attributeName === 'style') {
                        $codeview[0].style.height = this.$content[0].style.height;
                    }
                }
            });
            this.resizerHandleObserver.observe(this.$content[0], {attributes: true});
            $codeview.val(this.$content.html());
            this.wysiwyg.odooEditor.observerActive();
        }
    },
    /**
     * trigger_up 'field_changed' add record into the "ir.attachment" field found in the view.
     * This method is called when an image is uploaded via the media dialog.
     *
     * For e.g. when sending email, this allows people to add attachments with the content
     * editor interface and that they appear in the attachment list.
     * The new documents being attached to the email, they will not be erased by the CRON
     * when closing the wizard.
     *
     * @private
     * @param {Object} attachments
     */
    _onAttachmentChange: function (attachments) {
        if (!this.fieldNameAttachment) {
            return;
        }
        this.trigger_up('field_changed', {
            dataPointID: this.dataPointID,
            changes: _.object([this.fieldNameAttachment], [{
                operation: 'ADD_M2M',
                ids: attachments
            }])
        });
    },
    /**
     * @override
     */
    _renderEdit: function () {
        if (this.nodeOptions.notEditable) {
            return this._renderReadonly();
        }
        var value = this._textToHtml(this.value);
        if (this.nodeOptions.wrapper) {
            value = this._wrap(value);
        }
        var fieldNameAttachment = _.chain(this.recordData)
            .pairs()
            .find(function (value) {
                return _.isObject(value[1]) && value[1].model === "ir.attachment";
            })
            .first()
            .value();
        if (fieldNameAttachment) {
            this.fieldNameAttachment = fieldNameAttachment;
        }

        if (this.nodeOptions.cssEdit) {
            // must be async because the target must be append in the DOM
            this._createWysiwygIntance();
        } else {
            return this._createWysiwygIntance();
        }
    },
    /**
     * @override
     */
    _renderReadonly: function () {
        var self = this;
        var value = this._textToHtml(this.value);
        if (this.nodeOptions.wrapper) {
            value = this._wrap(value);
        }

        this.$el.empty();
        var resolver;
        var def = new Promise(function (resolve) {
            resolver = resolve;
        });
        if (this.nodeOptions.cssReadonly) {
            this.$iframe = $('<iframe class="o_readonly d-none"/>');
            this.$iframe.appendTo(this.$el);

            var avoidDoubleLoad = 0; // this bug only appears on some computers with some chrome version.

            // inject content in iframe

            this.$iframe.data('loadDef', def); // for unit test
            window.top[this._onUpdateIframeId] = function (_avoidDoubleLoad) {
                if (_avoidDoubleLoad !== avoidDoubleLoad) {
                    console.warn('Wysiwyg iframe double load detected');
                    return;
                }
                self.$content = $('#iframe_target', self.$iframe[0].contentWindow.document.body);
                resolver();
                self.trigger_up('iframe_updated', { $iframe: self.$iframe });
            };

            this.$iframe.on('load', function onLoad() {
                var _avoidDoubleLoad = ++avoidDoubleLoad;
                ajax.loadAsset(self.nodeOptions.cssReadonly).then(function (asset) {
                    if (_avoidDoubleLoad !== avoidDoubleLoad) {
                        console.warn('Wysiwyg immediate iframe double load detected');
                        return;
                    }
                    var cwindow = self.$iframe[0].contentWindow;
                    try {
                        cwindow.document;
                    } catch (e) {
                        return;
                    }
                    cwindow.document
                        .open("text/html", "replace")
                        .write(
                            '<!DOCTYPE html><html>' +
                            '<head>' +
                                '<meta charset="utf-8"/>' +
                                '<meta http-equiv="X-UA-Compatible" content="IE=edge,chrome=1"/>\n' +
                                '<meta name="viewport" content="width=device-width, initial-scale=1, user-scalable=no"/>\n' +
                                _.map(asset.cssLibs, function (cssLib) {
                                    return '<link type="text/css" rel="stylesheet" href="' + cssLib + '"/>';
                                }).join('\n') + '\n' +
                                _.map(asset.cssContents, function (cssContent) {
                                    return '<style type="text/css">' + cssContent + '</style>';
                                }).join('\n') + '\n' +
                            '</head>\n' +
                            '<body class="o_in_iframe o_readonly" style="overflow: hidden;">\n' +
                                '<div id="iframe_target">' + value + '</div>\n' +
                                '<script type="text/javascript">' +
                                    'if (window.top.' + self._onUpdateIframeId + ') {' +
                                        'window.top.' + self._onUpdateIframeId + '(' + _avoidDoubleLoad + ')' +
                                    '}' +
                                '</script>\n' +
                            '</body>' +
                            '</html>');

                    var height = cwindow.document.body.scrollHeight;
                    self.$iframe.css('height', Math.max(30, Math.min(height, 500)) + 'px');

                    $(cwindow).on('click', function (ev) {
                        if (!ev.target.closest("[href]")) {
                            self._onClick(ev);
                        }
                    });
                });
            });
        } else {
            this.$content = $('<div class="o_readonly"/>').html(value);
            this.$content.appendTo(this.$el);
            this._qwebPlugin = new QWebPlugin();
            this._qwebPlugin.sanitizeElement(this.$content[0]);
            resolver();
        }

        def.then(function () {
            self.$content.on('click', 'ul.o_checklist > li', self._onReadonlyClickChecklist.bind(self));
            if (self.$iframe) {
                // Iframe is hidden until fully loaded to avoid glitches.
                self.$iframe.removeClass('d-none');
            }
        });
    },
    /**
     * @private
     * @param {string} text
     * @returns {string} the text converted to html
     */
    _textToHtml: function (text) {
        var value = text || "";
        try {
            $(text)[0].innerHTML; // crashes if text isn't html
        } catch (e) {
            if (value.match(/^\s*$/)) {
                value = '<p><br/></p>';
            } else {
                value = "<p>" + value.split(/<br\/?>/).join("<br/></p><p>") + "</p>";
                value = value
                            .replace(/<p><\/p>/g, '')
                            .replace('<p><p>', '<p>')
                            .replace('<p><p ', '<p ')
                            .replace('</p></p>', '</p>');
            }
        }
        return value;
    },
    /**
     * Move HTML contents out of their wrapper.
     *
     * @private
     * @param {string} html content
     * @returns {string} html content
     */
    _unWrap: function (html) {
        var $wrapper = $(html).find('#wrapper');
        return $wrapper.length ? $wrapper.html() : html;
    },
    /**
     * Wrap HTML in order to create a custom display.
     *
     * The wrapper (this.nodeOptions.wrapper) must be a static
     * XML template with content id="wrapper".
     *
     * @private
     * @param {string} html content
     * @returns {string} html content
     */
    _wrap: function (html) {
        return $(QWeb.render(this.nodeOptions.wrapper))
            .find('#wrapper').html(html)
            .end().prop('outerHTML');
    },

    //--------------------------------------------------------------------------
    // Handler
    //--------------------------------------------------------------------------

    /**
     * Method called when wysiwyg triggers a change.
     *
     * @private
     * @param {OdooEvent} ev
     */
    _onChange: function (ev) {
        this._doDebouncedAction.apply(this, arguments);

        var $lis = this.$content.find('.note-editable ul.o_checklist > li:not(:has(> ul.o_checklist))');
        if (!$lis.length) {
            return;
        }
        var max = 0;
        var ids = [];
        $lis.map(function () {
            var checklistId = parseInt(($(this).attr('id') || '0').replace(/^checklist-id-/, ''));
            if (ids.indexOf(checklistId) === -1) {
                if (checklistId > max) {
                    max = checklistId;
                }
                ids.push(checklistId);
            } else {
                $(this).removeAttr('id');
            }
        });
        $lis.not('[id]').each(function () {
            $(this).attr('id', 'checklist-id-' + (++max));
        });
    },
    /**
     * Allows Enter keypress in a textarea (source mode)
     *
     * @private
     * @param {OdooEvent} ev
     */
    _onKeydown: function (ev) {
        if (ev.which === $.ui.keyCode.ENTER) {
            ev.stopPropagation();
            return;
        }
        this._super.apply(this, arguments);
    },
    /**
     * Method called when wysiwyg triggers a change.
     *
     * @private
     * @param {OdooEvent} ev
     */
    _onReadonlyClickChecklist: function (ev) {
        var self = this;
        if (ev.offsetX > 0) {
            return;
        }
        ev.stopPropagation();
        ev.preventDefault();
        var checked = $(ev.target).hasClass('o_checked');
        var checklistId = parseInt(($(ev.target).attr('id') || '0').replace(/^checklist-id-/, ''));

        this._rpc({
            route: '/web_editor/checklist',
            params: {
                res_model: this.model,
                res_id: this.res_id,
                filename: this.name,
                checklistId: checklistId,
                checked: !checked,
            },
        }).then(function (value) {
            self._setValue(value);
        });
    },
    /**
     * Method called when the wysiwyg instance is loaded.
     *
     * @private
     */
    _onLoadWysiwyg: function () {
        var $button = this._renderTranslateButton();
        $button.css({
            'font-size': '15px',
            position: 'absolute',
            right: odoo.debug && this.nodeOptions.codeview ? '40px' : '5px',
            top: '5px',
        });
        this.$el.append($button);
        if (odoo.debug && this.nodeOptions.codeview) {
            const $codeviewButtonToolbar = $(`
                <div id="codeview-btn-group" class="btn-group">
                    <button class="o_codeview_btn btn btn-primary">
                        <i class="fa fa-code"></i>
                    </button>
                </div>
            `);
            this.$floatingCodeViewButton = $codeviewButtonToolbar.clone();
            this._$codeview = $('<textarea class="o_codeview d-none"/>');
            this.wysiwyg.$editable.after(this._$codeview);
            this._$codeview.after(this.$floatingCodeViewButton);
            this.wysiwyg.toolbar.$el.append($codeviewButtonToolbar);
            $codeviewButtonToolbar.click(() => this._toggleCodeView(this._$codeview));
            this.$floatingCodeViewButton.click(() => this._toggleCodeView(this._$codeview));
        }
    },
    /**
     * @private
     * @param {OdooEvent} ev
     */
    _onWysiwygBlur: function (ev) {
        ev.stopPropagation();
        this._doAction();
        if (ev.data.key === 'TAB') {
            this.trigger_up('navigation_move', {
                direction: ev.data.shiftKey ? 'left' : 'right',
            });
        }
    },
    /**
     * @private
     * @param {OdooEvent} ev
     */
    _onWysiwygFocus: function (ev) {},
});


field_registry.add('html', FieldHtml);


return FieldHtml;
});
