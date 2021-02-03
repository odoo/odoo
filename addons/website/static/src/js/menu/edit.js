odoo.define('website.editMenu', function (require) {
'use strict';

var core = require('web.core');
var weContext = require('web_editor.context');
var editor = require('web_editor.editor');
var websiteNavbarData = require('website.navbar');

var _t = core._t;

/**
 * Adds the behavior when clicking on the 'edit' button (+ editor interaction)
 */
var EditPageMenu = websiteNavbarData.WebsiteNavbarActionWidget.extend({
    xmlDependencies: ['/website/static/src/xml/website.editor.xml'],
    actions: _.extend({}, websiteNavbarData.WebsiteNavbarActionWidget.prototype.actions, {
        edit: '_startEditMode',
        on_save: '_onSave',
    }),
    custom_events: _.extend({}, websiteNavbarData.WebsiteNavbarActionWidget.custom_events || {}, {
        content_will_be_destroyed: '_onContentWillBeDestroyed',
        content_was_recreated: '_onContentWasRecreated',
        snippet_will_be_cloned: '_onSnippetWillBeCloned',
        snippet_cloned: '_onSnippetCloned',
        snippet_dropped: '_onSnippetDropped',
    }),

    /**
     * @constructor
     */
    init: function () {
        this._super.apply(this, arguments);
        this._editorAutoStart = (weContext.getExtra().editable && window.location.search.indexOf('enable_editor') >= 0);
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
            this._startEditMode();
            return def;
        }

        // Check that the page is empty
        var $wrap = $('#wrapwrap.homepage #wrap'); // TODO find this element another way
        if (!$wrap.length || $wrap.html().trim() !== '') {
            return def;
        }

        // If readonly empty page, show the welcome message
        this.$welcomeMessage = $(core.qweb.render('website.homepage_editor_welcome_message'));
        this.$welcomeMessage.css('min-height', $wrap.parent('main').height() - ($wrap.outerHeight(true) - $wrap.height()));
        $wrap.empty().append(this.$welcomeMessage);

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
        return (new (editor.Class)(this)).prependTo(document.body).then(function () {
            if (self.$welcomeMessage) {
                self.$welcomeMessage.remove();
            }
            var $wrapwrap = $('#wrapwrap'); // TODO find this element another way
            self.$editorMessageElements = $wrapwrap.find('.oe_structure.oe_empty, [data-oe-type="html"]')
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
     * Called when content will be recreated in the page. Notifies the
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
     * Called when a snippet is about to be cloned in the page. Notifies the
     * WebsiteRoot that is should destroy the animations for this snippet.
     *
     * @private
     * @param {OdooEvent} ev
     */
    _onSnippetWillBeCloned: function (ev) {
        this.trigger_up('animation_stop_demand', {
            $target: ev.data.$target,
        });
    },
    /**
     * Called when a snippet is cloned in the page. Notifies the WebsiteRoot
     * that is should start the animations for this snippet and the snippet it
     * was cloned from.
     *
     * @private
     * @param {OdooEvent} ev
     */
    _onSnippetCloned: function (ev) {
        this.trigger_up('animation_start_demand', {
            editableMode: true,
            $target: ev.data.$target,
        });
        // TODO: remove in saas-12.5, undefined $origin will restart #wrapwrap
        if (ev.data.$origin) {
            this.trigger_up('animation_start_demand', {
                editableMode: true,
                $target: ev.data.$origin,
            });
        }
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
