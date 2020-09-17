odoo.define('website.editMenu', function (require) {
'use strict';

var core = require('web.core');
var websiteNavbarData = require('website.navbar');
var wysiwygLoader = require('web_editor.loader');
var ajax = require('web.ajax');
var Dialog = require('web.Dialog');
var localStorage = require('web.local_storage');
var _t = core._t;

var localStorageNoDialogKey = 'website_translator_nodialog';

var TranslatorInfoDialog = Dialog.extend({
    template: 'website.TranslatorInfoDialog',
    xmlDependencies: Dialog.prototype.xmlDependencies.concat(
        ['/website/static/src/xml/translator.xml']
    ),

    /**
     * @constructor
     */
    init: function (parent, options) {
        this._super(parent, _.extend({
            title: _t("Translation Info"),
            buttons: [
                {text: _t("Ok, never show me this again"), classes: 'btn-primary', close: true, click: this._onStrongOk.bind(this)},
                {text: _t("Ok"), close: true}
            ],
        }, options || {}));
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Called when the "strong" ok is clicked -> adapt localstorage to make sure
     * the dialog is never displayed again.
     *
     * @private
     */
    _onStrongOk: function () {
        localStorage.setItem(localStorageNoDialogKey, true);
    },
});

/**
 * Adds the behavior when clicking on the 'edit' button (+ editor interaction)
 */
var EditPageMenu = websiteNavbarData.WebsiteNavbarActionWidget.extend({
    assetLibs: ['web_editor.compiled_assets_wysiwyg', 'website.compiled_assets_wysiwyg'],
    xmlDependencies: ['/website/static/src/xml/website.editor.xml'],
    actions: _.extend({}, websiteNavbarData.WebsiteNavbarActionWidget.prototype.actions, {
        edit: '_startEditMode',
        on_save: '_onSave',
        translate: '_startTranslateMode',
        edit_master: '_goToMasterPage',
    }),
    custom_events: _.extend({}, websiteNavbarData.WebsiteNavbarActionWidget.custom_events || {}, {
        content_will_be_destroyed: '_onContentWillBeDestroyed',
        content_was_recreated: '_onContentWasRecreated',
        snippet_will_be_cloned: '_onSnippetWillBeCloned',
        snippet_cloned: '_onSnippetCloned',
        snippet_dropped: '_onSnippetDropped',
        edition_will_stopped: '_onEditionWillStop',
        edition_was_stopped: '_onEditionWasStopped',
        request_save: '_onSnippetRequestSave',
    }),

    /**
     * @constructor
     */
    init: function () {
        this._super.apply(this, arguments);
        var context;
        this.trigger_up('context_get', {
            extra: true,
            callback: function (ctx) {
                context = ctx;
            },
        });
        this._editorAutoStart = (context.editable && window.location.search.indexOf('enable_editor') >= 0);
        this._mustEditTranslations = context.edit_translations;

        if (this._mustEditTranslations) {
            var url = window.location.href.replace(/([?&])&*edit_translations[^&#]*&?/, '\$1');
            window.history.replaceState({}, null, url);
            this._startTranslateMode();
        } else {
            var url = window.location.href.replace(/([?&])&*enable_editor[^&#]*&?/, '\$1');
            window.history.replaceState({}, null, url);
        }
    },
    /**
     * Auto-starts the editor if necessary or add the welcome message otherwise.
     *
     * @override
     */
    start: async function () {
        var def = this._super.apply(this, arguments);

        // If we auto start the editor, do not show a welcome message
        if (this._editorAutoStart) {
            return Promise.all([def, this._startEditMode()]);
        }

        // Check that the page is empty
        var $wrap = this._targetForEdition().filter('#wrapwrap.homepage').find('#wrap');

        if ($wrap.length && $wrap.html().trim() === '') {
            // If readonly empty page, show the welcome message
            this.$welcomeMessage = $(core.qweb.render('website.homepage_editor_welcome_message'));
            this.$welcomeMessage.addClass('o_homepage_editor_welcome_message');
            this.$welcomeMessage.css('min-height', $wrap.parent('main').height() - ($wrap.outerHeight(true) - $wrap.height()));
            $wrap.empty().append(this.$welcomeMessage);
        }

        return def;
    },

    //--------------------------------------------------------------------------
    // Actions
    //--------------------------------------------------------------------------

    /**
     * Creates an editor instance and appends it to the DOM. Also remove the
     * welcome message if necessary.
     *
     * @private
     * @returns {Promise}
     */
    _startEditMode: async function () {
        // Add class in navbar and hide the navbar.
        this.trigger_up('edit_mode');

        if (this.editModeEnable) {
            return;
        }
        this.trigger_up('widgets_stop_request', {
            $target: this._targetForEdition(),
        });
        if (this.$welcomeMessage) {
            this.$welcomeMessage.detach(); // detach from the readonly rendering before the clone by summernote
        }
        this.editModeEnable = true;

        this.wysiwyg = await this._createWysiwyg();
        await this.wysiwyg.attachTo($('#wrapwrap'));

        var res = await new Promise((resolve, reject) => {
            this.trigger_up('widgets_start_request', {
                editableMode: true,
                onSuccess: resolve,
                onFailure: reject,
            });
        });
        // Trigger a mousedown on the main edition area to focus it,
        // which is required for Summernote to activate.
        return res;
    },
    /**
     * Redirects the user to the same page in translation mode (or start the
     * translator is translation mode is already enabled).
     *
     * @private
     * @returns {Promise}
     */
    _startTranslateMode: async function () {
        // Add class in navbar and hide the navbar.
        this.trigger_up('edit_mode');

        if (!this._mustEditTranslations) {
            window.location.search += '&edit_translations';
            return new Promise(function () {});
        }

        if (!localStorage.getItem(localStorageNoDialogKey)) {
            new TranslatorInfoDialog(this).open();
        }

        this.wysiwyg = await this._createWysiwyg(true);

        return this.wysiwyg.prependTo(document.body);
    },
    /**
     * @private
     * @param {boolean} [enableTranslation] true to create a translator wysiwyg.
     */
    _createWysiwyg: async function (enableTranslation = false) {
        var context;
        this.trigger_up('context_get', {
            callback: function (ctx) {
                context = ctx;
            },
        });

        const websiteToolbar = [
            ['TableButton'],
            ['OdooTextColorButton', 'OdooBackgroundColorButton'],
            [
                [
                    'ParagraphButton',
                    'Heading1Button',
                    'Heading2Button',
                    'Heading3Button',
                    'Heading4Button',
                    'Heading5Button',
                    'Heading6Button',
                    'PreButton',
                ],
            ],
            ['FontSizeInput'],
            [
                'BoldButton',
                'ItalicButton',
                'UnderlineButton',
                'RemoveFormatButton',
            ],
            ['AlignLeftButton', 'AlignCenterButton', 'AlignRightButton', 'AlignJustifyButton'],
            ['OrderedListButton', 'UnorderedListButton', 'ChecklistButton'],
            ['IndentButton', 'OutdentButton'],
            ['OdooLinkButton', 'UnlinkButton'],
            ['OdooMediaButton'],
            [
                [
                    'OdooImagePaddingNoneActionable',
                    'OdooImagePaddingSmallActionable',
                    'OdooImagePaddingMediumActionable',
                    'OdooImagePaddingLargeActionable',
                    'OdooImagePaddingXLActionable',
                ],
            ],
            [
                'OdooImageRoundedActionable',
                'OdooImageRoundedCircleActionable',
                'OdooImageRoundedShadowActionable',
                'OdooImageRoundedThumbnailActionable',
            ],
            [
                'OdooImageWidthAutoActionable',
                'OdooImageWidth25Actionable',
                'OdooImageWidth50Actionable',
                'OdooImageWidth75Actionable',
                'OdooImageWidth100Actionable',
            ],
            ['OdooCropActionable', 'OdooTransformActionable'],
            ['OdooDescriptionActionable'],
        ]
        const translationToolbar = [
            ['OdooTextColorButton', 'OdooBackgroundColorButton'],
            ['FontSizeInput'],
            [
                'BoldButton',
                'ItalicButton',
                'UnderlineButton',
            ],
        ]

        const params = {
            legacy: false,
            snippets: 'website.snippets',
            recordInfo: {
                context: context,
                data_res_model: 'website',
                data_res_id: context.website_id,
            }, value: $('#wrapwrap')[0].outerHTML,
            enableWebsite: true,
            discardButton: true,
            saveButton: true,
            devicePreview: true,
            toolbarLayout: enableTranslation ? translationToolbar : websiteToolbar,
            location: [document.getElementById('wrapwrap'), 'replace'],
        };
        params.enableTranslation = enableTranslation;

        return wysiwygLoader.createWysiwyg(this, params, ['website.compiled_assets_wysiwyg']);
    },
    /**
     * On save, the editor will ask to parent widgets if something needs to be
     * done first. The website navbar will receive that demand and asks to its
     * action-capable components to do something. For example, the content menu
     * handles page-related options saving. However, some users with limited
     * access rights do not have the content menu... but the website navbar
     * expects that the save action is performed. So, this empty action is
     * defined here so that all users have an 'on_save' related action.
     *
     * @private
     * @todo improve the system to somehow declare required/optional actions
     */
    _onSave: function () {},
    /**
     * Redirects the user to the same page but in the original language and in
     * edit mode.
     *
     * @private
     * @returns {Promise}
     */
    _goToMasterPage: function () {
        var current = document.createElement('a');
        current.href = window.location.toString();
        current.search += (current.search ? '&' : '?') + 'enable_editor=1';
        // we are in translate mode, the pathname starts with '/<url_code/'
        current.pathname = current.pathname.substr(current.pathname.indexOf('/', 1));

        var link = document.createElement('a');
        link.href = '/website/lang/default';
        link.search += (link.search ? '&' : '?') + 'r=' + encodeURIComponent(current.pathname + current.search + current.hash);

        window.location = link.href;
        return new Promise(function () {});
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Returns the target for edition.
     *
     * @private
     * @returns {JQuery}
     */
    _targetForEdition: function () {
        return $('#wrapwrap'); // TODO should know about this element another way
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Called when content will be destroyed in the page. Notifies the
     * WebsiteRoot that is should stop the public widgets.
     *
     * @private
     * @param {OdooEvent} ev
     */
    _onContentWillBeDestroyed: function (ev) {
        this.trigger_up('widgets_stop_request', {
            $target: ev.data.$target,
        });
    },
    /**
     * Called when content was recreated in the page. Notifies the
     * WebsiteRoot that is should start the public widgets.
     *
     * @private
     * @param {OdooEvent} ev
     */
    _onContentWasRecreated: function (ev) {
        this.trigger_up('widgets_start_request', {
            editableMode: true,
            $target: ev.data.$target,
        });
    },
    /**
     * Called when edition will stop. Notifies the
     * WebsiteRoot that is should stop the public widgets.
     *
     * @private
     * @param {OdooEvent} ev
     */
    _onEditionWillStop: function (ev) {
        this.$editorMessageElements && this.$editorMessageElements.removeAttr('data-editor-message');
        this.trigger_up('widgets_stop_request', {
            $target: this._targetForEdition(),
        });
    },
    /**
     * Called when edition was stopped. Notifies the
     * WebsiteRoot that is should start the public widgets.
     *
     * @private
     * @param {OdooEvent} ev
     */
    _onEditionWasStopped: function (ev) {
        this.trigger_up('widgets_start_request', {
            $target: this._targetForEdition(),
        });
        this.editModeEnable = false;
    },
    /**
     * Called when a snippet is about to be cloned in the page. Notifies the
     * WebsiteRoot that is should destroy the animations for this snippet.
     *
     * @private
     * @param {OdooEvent} ev
     */
    _onSnippetWillBeCloned: function (ev) {
        this.trigger_up('widgets_stop_request', {
            $target: ev.data.$target,
        });
    },
    /**
     * Called when a snippet is cloned in the page. Notifies the WebsiteRoot
     * that is should start the public widgets for this snippet and the snippet it
     * was cloned from.
     *
     * @private
     * @param {OdooEvent} ev
     */
    _onSnippetCloned: function (ev) {
        this.trigger_up('widgets_start_request', {
            editableMode: true,
            $target: ev.data.$target,
        });
        // TODO: remove in saas-12.5, undefined $origin will restart #wrapwrap
        if (ev.data.$origin) {
            this.trigger_up('widgets_start_request', {
                editableMode: true,
                $target: ev.data.$origin,
            });
        }
    },
    /**
     * Called when a snippet is dropped in the page. Notifies the WebsiteRoot
     * that is should start the public widgets for this snippet. Also add the
     * editor messages.
     *
     * @private
     * @param {OdooEvent} ev
     */
    _onSnippetDropped: function (ev) {
        this.trigger_up('widgets_start_request', {
            editableMode: true,
            $target: ev.data.$target,
        });
        // this._addEditorMessages();
    },
    /**
     * Snippet (menu_data) can request to save the document to leave the page
     *
     * @private
     * @param {OdooEvent} ev
     * @param {object} ev.data
     * @param {function} ev.data.onSuccess
     * @param {function} ev.data.onFailure
     */
    _onSnippetRequestSave: function (ev) {
        this.wysiwyg.saveToServer(undefined, false).then(ev.data.onSuccess, ev.data.onFailure);
    },
});

websiteNavbarData.websiteNavbarRegistry.add(EditPageMenu, '#edit-page-menu,.o_menu_systray:has([data-action="translate"])');
});
