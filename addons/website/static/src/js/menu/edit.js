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
    }),
    custom_events: _.extend({}, websiteNavbarData.WebsiteNavbarActionWidget.custom_events || {}, {
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
            $wrapwrap.find('.oe_structure.oe_empty, [data-oe-type="html"]').attr('data-editor-message', _t('DRAG BUILDING BLOCKS HERE'));
            var def = $.Deferred();
            self.trigger_up('animation_start_demand', {
                editableMode: true,
                onSuccess: def.resolve.bind(def),
                onFailure: def.reject.bind(def),
            });
            return def;
        });
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

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
