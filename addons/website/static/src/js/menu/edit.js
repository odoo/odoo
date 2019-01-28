odoo.define('website.editMenu', function (require) {
'use strict';

var core = require('web.core');
var EditorMenu = require('website.editor.menu');
var websiteNavbarData = require('website.navbar');

var _t = core._t;

/**
 * Adds the behavior when clicking on the 'edit' button (+ editor interaction)
 */
var EditPageMenu = websiteNavbarData.WebsiteNavbarActionWidget.extend({
    assetLibs: ['web_editor.compiled_assets_wysiwyg', 'website.compiled_assets_wysiwyg'],

    xmlDependencies: ['/website/static/src/xml/website.editor.xml'],
    actions: _.extend({}, websiteNavbarData.WebsiteNavbarActionWidget.prototype.actions, {
        edit: '_startEditMode',
        on_save: '_onSave',
    }),
    custom_events: _.extend({}, websiteNavbarData.WebsiteNavbarActionWidget.custom_events || {}, {
        content_will_be_destroyed: '_onContentWillBeDestroyed',
        content_was_recreated: '_onContentWasRecreated',
        snippet_cloned: '_onSnippetCloned',
        snippet_dropped: '_onSnippetDropped',
        edition_will_stopped: '_onEditionWillStop',
        edition_was_stopped: '_onEditionWasStopped',
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
    },
    /**
     * Auto-starts the editor if necessary or add the welcome message otherwise.
     *
     * @override
     */
    start: function () {
        var def = this._super.apply(this, arguments);

        // If we auto start the editor, do not show a welcome message
        if (this._editorAutoStart) {
            return $.when(def, this._startEditMode());
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

        setTimeout(function () {
            if ($('.o_tooltip.o_animated').length) {
                $('.o_tooltip_container').addClass('show');
            }
        }, 1000); // ugly hack to wait that tooltip is loaded

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
     * @returns {Deferred}
     */
    _startEditMode: function () {
        var self = this;
        this.trigger_up('animation_stop_demand', {
            $target: this._targetForEdition(),
        });
        var $welcomeMessageParent = null;
        if (this.$welcomeMessage) {
            $welcomeMessageParent = this.$welcomeMessage.parent();
            this.$welcomeMessage.detach(); // detach from the readonly rendering before the clone by summernote
        }
        return new EditorMenu(this).prependTo(document.body).then(function () {
            if (self.$welcomeMessage) {
                $welcomeMessageParent.append(self.$welcomeMessage); // reappend if the user cancel the edition
            }

            var $target = self._targetForEdition();
            self.$editorMessageElements = $target
                .find('.oe_structure.oe_empty, [data-oe-type="html"]')
                .not('[data-editor-message]')
                .attr('data-editor-message', _t('DRAG BUILDING BLOCKS HERE'));
            var def = $.Deferred();
            self.trigger_up('animation_start_demand', {
                editableMode: true,
                onSuccess: def.resolve.bind(def),
                onFailure: def.reject.bind(def),
            });
            return def;
        });
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
     * As explained above, that action should always be defined in the current
     * implementation (even an empty one) but in fact it is also needed to
     * remove the data-editor-message attributes which are added when entering
     * edition.
     *
     * @private
     * @todo improve the system to somehow declare required/optional actions
     */
    _onSave: function () {
        if (this.$editorMessageElements) {
            this.$editorMessageElements.removeAttr('data-editor-message');
        }
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
     * WebsiteRoot that is should stop the animations.
     *
     * @private
     * @param {OdooEvent} ev
     */
    _onContentWillBeDestroyed: function (ev) {
        this.trigger_up('animation_stop_demand', {
            $target: ev.data.$target,
        });
    },
    /**
     * Called when content was recreated in the page. Notifies the
     * WebsiteRoot that is should start the animations.
     *
     * @private
     * @param {OdooEvent} ev
     */
    _onContentWasRecreated: function (ev) {
        this.trigger_up('animation_start_demand', {
            editableMode: true,
            $target: ev.data.$target,
        });
    },
    /**
     * Called when edition will stop. Notifies the
     * WebsiteRoot that is should stop the animations.
     *
     * @private
     * @param {OdooEvent} ev
     */
    _onEditionWillStop: function (ev) {
        this.$editorMessageElements.removeAttr('data-editor-message');
        this.trigger_up('animation_stop_demand', {
            $target: this._targetForEdition(),
        });
    },
    /**
     * Called when edition was stopped. Notifies the
     * WebsiteRoot that is should start the animations.
     *
     * @private
     * @param {OdooEvent} ev
     */
    _onEditionWasStopped: function (ev) {
        this.trigger_up('animation_start_demand', {
            $target: this._targetForEdition(),
        });
    },
    /**
     * Called when a snippet is cloned in the page. Notifies the WebsiteRoot
     * that is should start the animations for this snippet.
     *
     * @private
     * @param {OdooEvent} ev
     */
    _onSnippetCloned: function (ev) {
        this.trigger_up('animation_start_demand', {
            editableMode: true,
            $target: ev.data.$target,
        });
    },
    /**
     * Called when a snippet is dropped in the page. Notifies the WebsiteRoot
     * that is should start the animations for this snippet.
     *
     * @private
     * @param {OdooEvent} ev
     */
    _onSnippetDropped: function (ev) {
        this.trigger_up('animation_start_demand', {
            editableMode: true,
            $target: ev.data.$target,
        });
    },
});

websiteNavbarData.websiteNavbarRegistry.add(EditPageMenu, '#edit-page-menu');
});
