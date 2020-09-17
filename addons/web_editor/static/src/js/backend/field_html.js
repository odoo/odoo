odoo.define('web_editor.field.html', function (require) {
'use strict';

var ajax = require('web.ajax');
var basic_fields = require('web.basic_fields');
var core = require('web.core');
var wysiwygLoader = require('web_editor.loader');
var field_registry = require('web.field_registry');
// must wait for web/ to add the default html widget, otherwise it would override the web_editor one
require('web._field_registry');

var _lt = core._lt;
var TranslatableFieldMixin = basic_fields.TranslatableFieldMixin;
var QWeb = core.qweb;

var jinjaRegex = /(^|\n)\s*%\s(end|set\s)/;

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
 */
var FieldHtml = basic_fields.DebouncedField.extend(TranslatableFieldMixin, {
    description: _lt("Html"),
    className: 'oe_form_field oe_form_field_html d-flex',
    supportedFieldTypes: ['html'],

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
        await this._super();
        if (this.nodeOptions.cssReadonly) {
            this.cssReadonly = await ajax.loadAsset(this.nodeOptions.cssReadonly);
        }
        if (this.nodeOptions.cssEdit || this.nodeOptions['style-inline']) {
            this.needShadow = true;
            this.cssEdit = await ajax.loadAsset(this.nodeOptions.cssEdit || 'web_editor.assets_edit_html_field');
        }
    },
    /**
     * @override
     */
    destroy: function () {
        if (this.$iframe) {
            this.$iframe.remove();
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
    commitChanges: async function () {
        var _super = this._super.bind(this);
        if (this.mode === "readonly" || !this.wysiwyg) {
            return _super();
        }
        this._isDirty = await this.wysiwyg.isDirty();
        // todo: make this work
        const promise = this.wysiwyg.getValue(this.nodeOptions['style-inline'] ? 'text/mail' : 'text/html');
        promise.catch(error => {
            console.error(error);
        });
        this._value = await promise;
        return _super();
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
        return this.$el;
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
            if (this.mode === 'edit') {
                if (this.wysiwyg) {
                    this.wysiwyg.setValue(value);
                } else {
                    this._value = value;
                }
            } else {
                this.$readOnlyContainer.html(value);
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
        return this._value;
    },
    /**
     * Create the wysiwyg instance with the target (this.$editorContainer)
     * then add the editable content (this.$readOnlyContainer).
     *
     * @private
     * @returns {$.Promise}
     */
    _createWysiwygIntance: async function () {
        this.wysiwyg = await wysiwygLoader.createWysiwyg(this, await this._getWysiwygOptions());
        return this.wysiwyg.attachTo(this).then(() => {
            this._appendTranslateButton();
        });
    },
    /**
     * Get wysiwyg options to create wysiwyg instance.
     *
     * @private
     * @returns {Object}
     */
    _getWysiwygOptions: async function () {
        let main = '<t t-zone="main"/>';

        if (this.needShadow) {
            let style = '';
            if (this.cssEdit) {
                // wether to inject or not assets in an iframe
                style = [
                    ...this.cssEdit.cssLibs.map(cssLib => '<link type="text/css" rel="stylesheet" href="' + cssLib + '"/>'),
                    ...this.cssEdit.cssContents.map(cssContent => {
                        const clean = cssContent.replace(/\/\*.*\*\//g, '');
                        return '<style type="text/css">' + clean + '</style>';
                    }),
                ].join('');
            }
            main = '<t-shadow style="width: 100%;">' + style + '\n' + main + '</t-shadow>';
        }

        return Object.assign({}, this.nodeOptions, {
            recordInfo: {
                context: this.record.getContext(this.recordParams),
                res_model: this.model,
                res_id: this.res_id,
            },
            noAttachment: this.nodeOptions['no-attachment'],
            snippets: this.nodeOptions.snippets,
            value: this.value || '',
            location: [this.el, 'append'],
            wrapperClass: 'note-editable',
            interface: `
                <t-dialog><t t-zone="default"/></t-dialog>
                <t-range><t t-zone="tools"/></t-range>
                <div class="d-flex flex-column flex-grow-1">
                    <div class="d-flex flex-row overflow-auto">
                        <t t-zone="container">
                            <t t-zone="main_sidebar"/>
                            <div class="d-flex flex-column overflow-auto o_editor_center">
                                <div class="d-flex overflow-auto note-editing-area d-flex flex-grow-1">
                                    <t t-zone="snippetManipulators"/>
                                    ` + main + `
                                </div>
                            </div>
                        </t>
                    </div>
                    <div class="o_debug_zone">
                        <t t-zone="debug"/>
                    </div>
                </div>`,
        });
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
        if (this.attrs.class && this.attrs.class.indexOf("oe_read_only") !== -1) {
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
        return this._createWysiwygIntance();
    },
    /**
     * @override
     */
    _renderReadonly: function () {
        var value = this._textToHtml(this.value);
        if (this.nodeOptions.wrapper) {
            value = this._wrap(value);
        }

        this.$el.empty();
        if (this.nodeOptions.cssReadonly) {
            const shadowRoot = this.$el[0].attachShadow({mode: 'open'});
            for (const cssLib of this.cssReadonly.cssLibs) {
                const link = $('<link type="text/css" rel="stylesheet" href="' + cssLib + '"/>')[0];
                shadowRoot.appendChild(link);
            }
            for (const cssContent of this.cssReadonly.cssContents) {
                const style = $('<style type="text/css">' + cssContent + '</style>')[0];
                shadowRoot.appendChild(style);
            }
            const container = document.createElement('container');
            container.innerHTML = value;
            for (const node of [...container.childNodes]) {
                shadowRoot.appendChild(node);
            }
        } else {
            this.$readOnlyContainer = $('<div class="o_readonly"/>').html(value);
            this.$readOnlyContainer.appendTo(this.$el);
        }

    },
    /**
     * @private
     * @param {string} text
     * @returns {string} the text converted to html
     */
    _textToHtml: function (text) {
        var value = text || "";
        if (jinjaRegex.test(value) || text === '') { // is jinja
            return value;
        }
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
    },
    /**
     * Append the translate button to the DOM.
     * This method is called when the wysiwyg instance is loaded.
     *
     * @private
     */
    _appendTranslateButton: function () {
        var $button = this._renderTranslateButton();
        $button.css({
            'font-size': '15px',
            position: 'absolute',
            right: '+5px',
            top: '+5px',
        });
        this.$el.append($button);
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

    /**
    * Stops the enter navigation in an html field.
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
});


field_registry.add('html', FieldHtml);


return FieldHtml;
});
