/** @odoo-module */

import core from 'web.core';
import Widget from 'web.Widget';
import Dialog from "web.Dialog";
import utils from 'web.utils';
import { KnowledgeMacro } from './knowledge_macros';
import { sprintf } from '@web/core/utils/strings';
const _t = core._t;

/**
 * Toolbar to be injected through @see FieldHtmlInjector to @see OdooEditor
 * blocks which have specific classes calling for such toolbars.
 *
 * A typical usage could be the following:
 * - An @see OdooEditor block like /template has the generic class:
 *   @see o_knowledge_toolbars_container to signify that some of its children need
 *   to have toolbars injected.
 * - At least one of the children has the generic class:
 *   @see o_knowledge_toolbar_anchor that is a container in which the toolbar
 *   will be appended
 * - The same child also as the specific class:
 *   @see o_knowledge_toolbar_type_[toolbarType] which specifies the type of the
 *   toolbar that needs to be injected. @see FieldHtmlInjector has a dictionary
 *   mapping those classes to the correct toolbar class.
 *
 * The @see KnowledgeToolbar is a basic toolbar intended to be overriden for
 * more complex implementations
 *
 * This widget should be converted to a component.
 */
const KnowledgeToolbar = Widget.extend({
    /**
     * @override
     * @param {Widget} parent
     * @param {Element} container root node of the @see OdooEditor block, i.e.:
     *                        /template or /file root container
     * @param {Element} anchor sub-child of @see container container of the
     *                         toolbar
     * @param {string} template
     * @param {Object} editor @see OdooEditor
     * @param {Object} uiService when this widget is converted to a component,
     *                           uiService won't be needed as a parameter
     */
    init: function (parent, container, anchor, template, editor, uiService) {
        this._super.apply(this, [parent]);
        this.container = container;
        this.anchor = anchor;
        this.template = template;
        this.mode = parent.mode;
        this.field = parent.field;
        this.editor = editor;
        this.uiService = uiService;
    },
    /**
     * Used by @see KnowledgePlugin to remove toolbars when the field_html is
     * saved. Also used by @see FieldHtmlInjector to manage injected toolbars
     */
    removeToolbar: function () {
        this.trigger_up('toolbar_removed', {
            anchor: this.anchor,
        });
        delete this.anchor.oKnowledgeToolbar;
        this.destroy();
    },
    /**
     * @override
     */
    start: function () {
        const prom = this._super.apply(this, arguments);
        return prom.then(function () {
            this._setupButtons();
        }.bind(this));
    },
    /**
     * Setup the toolbar buttons
     */
    _setupButtons: function () {
        const buttons = this.el.querySelectorAll('button');
        buttons.forEach(this._setupButton.bind(this));
    },
    // FUNCTIONS TO OVERRIDE \\
    /**
     * Called for each button of the toolbar. Each button should have a
     * data-call attribute which is used as a unique key for differentiation.
     * A common implementation would be a switch case on "button.dataset.call".
     * Intercept dblclick events to avoid @see OdooEditor interference
     *
     * @param {Element} button
     */
    _setupButton: function (button) {
        button.addEventListener("dblclick", function (ev) {
            ev.stopPropagation();
            ev.preventDefault();
        });
        return;
    },
});

/**
 * Toolbar for the /file command
 */
const FileToolbar = KnowledgeToolbar.extend({
    /**
     * Recover the eventual related record from @see KnowledgeService
     *
     * @override
     */
    init: function () {
        this._super.apply(this, arguments);
        this.recordWithChatter = this.call('knowledgeService', 'getAvailableRecordWithChatter');
    },
    /**
     * Get data from the file related to this toolbar
     *
     * @param {Element} fileLink <a> element to extract file data from
     */
    _fetchData: async function (fileLink) {
        if (!fileLink || !fileLink.href) {
            return null;
        }
        return await fetch(fileLink.href).then(async function (response) {
            if (response.ok) {
                return await response.blob();
            } else {
                return null;
            }
        });
    },
    /**
     * @override
     */
    _setupButton: function (button) {
        this._super.apply(this, arguments);
        switch (button.dataset.call) {
            /**
             * Create a @see KnowledgeMacro to add the file to a new message
             * in the context of the related record.
             */
            case 'attach_to_message':
                button.addEventListener("click", async function(ev) {
                    ev.stopPropagation();
                    ev.preventDefault();
                    const record = this.recordWithChatter;
                    if (record) {
                        const fileLink = this.container.querySelector('.o_knowledge_file_image > a');
                        const data = await this._fetchData(fileLink);
                        if (!data) {
                            return;
                        }
                        const file = new File([data], fileLink.getAttribute('title'), { type: data.type });
                        /**
                         * dataTransfer will be used to mimic a drag and drop of
                         * the file in the target record chatter.
                         * @see KnowledgeMacro
                         */
                        const dataTransfer = new DataTransfer();
                        dataTransfer.items.add(file);
                        let macro = new KnowledgeMacro(record.breadcrumbs, button.dataset.call, {
                            dataTransfer: dataTransfer,
                        }, this.uiService);
                        macro.start();
                    }
                }.bind(this));
                break;
            /**
             * Create a @see KnowledgeMacro to add the file as an attachment of
             * the related record.
             */
            case 'use_as_attachment':
                button.addEventListener("click", async function(ev) {
                    ev.stopPropagation();
                    ev.preventDefault();
                    const record = this.recordWithChatter;
                    if (record) {
                        const fileLink = this.container.querySelector('.o_knowledge_file_image > a');
                        const data = await this._fetchData(fileLink);
                        if (!data) {
                            return;
                        }
                        const dataURL = await utils.getDataURLFromFile(data);
                        const attachment = await this._rpc({
                            route: '/web_editor/attachment/add_data',
                            params: {
                                'name': fileLink.getAttribute('title'),
                                'data': dataURL.split(',')[1],
                                'is_image': false,
                                'res_id': this.recordWithChatter.res_id,
                                'res_model': this.recordWithChatter.res_model,
                            }
                        });
                        if (!attachment) {
                            return;
                        }
                        let macro = new KnowledgeMacro(record.breadcrumbs, button.dataset.call, {}, this.uiService);
                        macro.start();
                    }
                }.bind(this));
                break;
            /**
             * Add the file download behavior to the button and the image link
             */
            case 'download':
                const download = async function (ev) {
                    ev.stopPropagation();
                    ev.preventDefault();
                    // Roundabout way to click on the link, to avoid OdooEditor interference with the event
                    const downloadLink = document.createElement('a');
                    const originalLink = this.container.querySelector('.o_knowledge_file_image > a');
                    const title = originalLink.getAttribute('title') ? `"${originalLink.getAttribute('title')}" `: "";
                    const href = originalLink.getAttribute('href');
                    const response = await fetch(href).then((response) => response);
                    if (response.ok) {
                        downloadLink.setAttribute('href', href);
                        downloadLink.setAttribute('download', '');
                        downloadLink.setAttribute('target', '_blank');
                        downloadLink.click();
                    } else {
                        Dialog.alert(this,
                            sprintf(_t('Oops, the file %s could not be found. Please replace this file box by a new one to re-upload the file.'), title), {
                            title: _t('Missing File'),
                            buttons: [{
                                text: _t('Close'),
                                close: true,
                            }]
                        });
                    }
                }.bind(this);
                button.addEventListener("click", download);
                const imageElement = this.container.querySelector('.o_knowledge_file_image');
                if (!imageElement.oKnowledgeClickListener) {
                    imageElement.addEventListener("click", download);
                    imageElement.oKnowledgeClickListener = true;
                }
                break;
        }
    },
});

/**
 * Toolbar for the /template command
 */
const TemplateToolbar = KnowledgeToolbar.extend({
    /**
     * Recover the eventual related records from @see KnowledgeService
     *
     * @override
     */
    init: function () {
        this._super.apply(this, arguments);
        this.recordWithChatter = this.call('knowledgeService', 'getAvailableRecordWithChatter');
        this.recordWithHtmlField = this.call('knowledgeService', 'getAvailableRecordWithHtmlField');
    },
    /**
     * Create a dataTransfer object with the editable content of the template
     * block, to be used for a paste event in the editor
     */
    _createHtmlDataTransfer: function () {
        const dataTransfer = new DataTransfer();
        const content = this.container.querySelector('.o_knowledge_content');
        dataTransfer.setData('text/html', content.outerHTML);
        return dataTransfer;
    },
    /**
     * @override
     */
    _setupButton: function (button) {
        this._super.apply(this, arguments);
        switch (button.dataset.call) {
            /**
             * Create a @see KnowledgeMacro to copy the content of the /template
             * block and paste it as the content of a new message in the context
             * of the related record, in a fullComposer form dialog
             */
            case 'send_as_message':
                button.addEventListener("click", function (ev) {
                    ev.stopPropagation();
                    ev.preventDefault();
                    const record = this.recordWithChatter;
                    if (record) {
                        const dataTransfer = this._createHtmlDataTransfer();
                        let macro = new KnowledgeMacro(record.breadcrumbs, button.dataset.call, {
                            dataTransfer: dataTransfer,
                        }, this.uiService);
                        macro.start();
                    }
                }.bind(this));
                break;
            /**
             * Create a @see KnowledgeMacro to copy the content of the /template
             * block and paste it as the content (prepend) of the field_html
             * value of the related record
             */
            case 'use_as_description':
                button.addEventListener("click", function(ev) {
                    ev.stopPropagation();
                    ev.preventDefault();
                    const record = this.recordWithHtmlField;
                    if (record) {
                        const dataTransfer = this._createHtmlDataTransfer();
                        let macro = new KnowledgeMacro(record.breadcrumbs, button.dataset.call, {
                            fieldName: record.fieldNames[0].name,
                            dataTransfer: dataTransfer,
                        }, this.uiService);
                        macro.start();
                    }
                }.bind(this));
                break;
            /**
             * Copy the content of the /template block to the clipboard, and
             * prevent @see OdooEditor interference
             */
            case 'copy_to_clipboard':
                button.addEventListener("click", function (ev) {
                    ev.stopPropagation();
                    ev.preventDefault();
                });
                const content = this.container.querySelector('.o_knowledge_content');
                const clipboard = new ClipboardJS(
                    button,
                    {target: () => content}
                );
                clipboard.on('success', (e) => {
                    e.clearSelection();
                    this.displayNotification({
                        type: 'success',
                        message: _t("Template copied to clipboard."),
                    });
                });
                break;
        }
    },
});

export {
    TemplateToolbar,
    FileToolbar,
    KnowledgeToolbar,
};
