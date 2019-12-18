odoo.define('web_editor.snippet.editor', function (require) {
'use strict';

var concurrency = require('web.concurrency');
var core = require('web.core');
var Dialog = require('web.Dialog');
var dom = require('web.dom');
var Widget = require('web.Widget');
var options = require('web_editor.snippets.options');
var Wysiwyg = require('web_editor.wysiwyg');

var _t = core._t;

var globalSelector = {
    closest: () => $(),
    all: () => $(),
    is: () => false,
};

/**
 * Management of the overlay and option list for a snippet.
 */
var SnippetEditor = Widget.extend({
    template: 'web_editor.snippet_overlay',
    xmlDependencies: ['/web_editor/static/src/xml/snippets.xml'],
    custom_events: {
        'option_update': '_onOptionUpdate',
        'user_value_widget_request': '_onUserValueWidgetRequest',
        'snippet_option_update': '_onSnippetOptionUpdate',
        'snippet_option_visibility_update': '_onSnippetOptionVisibilityUpdate',
    },

    /**
     * @constructor
     * @param {Widget} parent
     * @param {Element} target
     * @param {Object} templateOptions
     * @param {jQuery} $editable
     * @param {Object} options
     */
    init: function (parent, target, templateOptions, $editable, options) {
        this._super.apply(this, arguments);
        this.options = options;
        this.$editable = $editable;
        this.ownerDocument = this.$editable[0].ownerDocument;
        this.$body = $(this.ownerDocument.body);
        this.$target = $(target);
        this.$target.data('snippet-editor', this);
        this.templateOptions = templateOptions;
        this.isTargetParentEditable = false;
        this.isTargetMovable = false;

        this.__isStarted = new Promise(resolve => {
            this.__isStartedResolveFunc = resolve;
        });
    },
    /**
     * @override
     */
    start: function () {
        var defs = [this._super.apply(this, arguments)];

        // Initialize the associated options (see snippets.options.js)
        defs.push(this._initializeOptions());
        var $customize = this._customize$Elements[this._customize$Elements.length - 1];

        this.isTargetParentEditable = this.$target.parent().is(':o_editable');
        this.isTargetMovable = this.isTargetParentEditable && this.isTargetMovable;

        // Initialize move/clone/remove buttons
        if (this.isTargetMovable) {
            this.dropped = false;
            this.$el.draggable({
                greedy: true,
                appendTo: this.$body,
                cursor: 'move',
                handle: '.o_move_handle',
                cursorAt: {
                    left: 18,
                    top: 14
                },
                helper: () => {
                    var $clone = this.$el.clone().css({width: '24px', height: '24px', border: 0});
                    $clone.appendTo(this.$body).removeClass('d-none');
                    return $clone;
                },
                start: this._onDragAndDropStart.bind(this),
                stop: (...args) => {
                    // Delay our stop handler so that some summernote handlers
                    // which occur on mouseup (and are themself delayed) are
                    // executed first (this prevents the library to crash
                    // because our stop handler may change the DOM).
                    setTimeout(() => {
                        this._onDragAndDropStop(...args);
                    }, 0);
                },
            });
        } else {
            this.$('.o_move_handle').addClass('d-none');
            $customize.find('.oe_snippet_clone').addClass('d-none');
        }

        if (!this.isTargetParentEditable) {
            $customize.find('.oe_snippet_remove').addClass('d-none');
        }

        var _animationsCount = 0;
        var postAnimationCover = _.throttle(() => this.cover(), 100);
        this.$target.on('transitionstart.snippet_editor, animationstart.snippet_editor', () => {
            // We cannot rely on the fact each transition/animation start will
            // trigger a transition/animation end as the element may be removed
            // from the DOM before or it could simply be an infinite animation.
            //
            // By simplicity, for each start, we add a delayed operation that
            // will decrease the animation counter after a fixed duration and
            // do the post animation cover if none is registered anymore.
            _animationsCount++;
            setTimeout(() => {
                if (!--_animationsCount) {
                    postAnimationCover();
                }
            }, 500); // This delay have to be huge enough to take care of long
                     // animations which will not trigger an animation end event
                     // but if it is too small for some, this is the job of the
                     // animation creator to manually ask for a re-cover
        });
        // On top of what is explained above, do the post animation cover for
        // each detected transition/animation end so that the user does not see
        // a flickering when not needed.
        this.$target.on('transitionend.snippet_editor, animationend.snippet_editor', postAnimationCover);

        return Promise.all(defs).then(() => {
            this.__isStartedResolveFunc(this);
        });
    },
    /**
     * @override
     */
    destroy: function () {
        this._super(...arguments);
        this.$target.removeData('snippet-editor');
        this.$target.off('.snippet_editor');
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Checks whether the snippet options are shown or not.
     *
     * @returns {boolean}
     */
    areOptionsShown: function () {
        const lastIndex = this._customize$Elements.length - 1;
        return !!this._customize$Elements[lastIndex].parent().length;
    },
    /**
     * Notifies all the associated snippet options that the snippet has just
     * been dropped in the page.
     */
    buildSnippet: async function () {
        for (var i in this.styles) {
            this.styles[i].onBuilt();
        }
        await this.toggleTargetVisibility(true);
    },
    /**
     * Notifies all the associated snippet options that the template which
     * contains the snippet is about to be saved.
     */
    cleanForSave: async function () {
        if (this.isDestroyed()) {
            return;
        }
        await this.toggleTargetVisibility(!this.$target.hasClass('o_snippet_invisible'));
        const proms = _.map(this.styles, option => {
            return option.cleanForSave();
        });
        await Promise.all(proms);
    },
    /**
     * Closes all widgets of all options.
     */
    closeWidgets: function () {
        if (!this.areOptionsShown()) {
            return;
        }
        Object.keys(this.styles).forEach(key => {
            this.styles[key].closeWidgets();
        });
    },
    /**
     * Makes the editor overlay cover the associated snippet.
     */
    cover: function () {
        if (!this.isShown() || !this.$target.length || !this.$target.is(':visible')) {
            return;
        }
        var offset = this.$target.offset();
        var manipulatorOffset = this.$el.parent().offset();
        offset.top -= manipulatorOffset.top;
        offset.left -= manipulatorOffset.left;
        this.$el.css({
            width: this.$target.outerWidth(),
            left: offset.left,
            top: offset.top,
        });
        this.$('.o_handles').css('height', this.$target.outerHeight());
        this.$el.toggleClass('o_top_cover', offset.top < this.$editable.offset().top);
    },
    /**
     * DOMElements have a default name which appears in the overlay when they
     * are being edited. This method retrieves this name; it can be defined
     * directly in the DOM thanks to the `data-name` attribute.
     */
    getName: function () {
        if (this.$target.data('name') !== undefined) {
            return this.$target.data('name');
        }
        if (this.$target.parent('.row').length) {
            return _t("Column");
        }
        return _t("Block");
    },
    /**
     * @return {boolean}
     */
    isShown: function () {
        return this.$el && this.$el.parent().length && this.$el.hasClass('oe_active');
    },
    /**
     * @returns {boolean}
     */
    isTargetVisible: function () {
        return (this.$target[0].dataset.invisible !== '1');
    },
    /**
     * Removes the associated snippet from the DOM and destroys the associated
     * editor (itself).
     */
    removeSnippet: function () {
        this.toggleOverlay(false);
        this.toggleOptions(false);

        this.trigger_up('call_for_each_child_snippet', {
            $snippet: this.$target,
            callback: function (editor, $snippet) {
                for (var i in editor.styles) {
                    editor.styles[i].onRemove();
                }
            },
        });

        this.trigger_up('go_to_parent', {$snippet: this.$target});
        var $parent = this.$target.parent();
        this.$target.find('*').addBack().tooltip('dispose');
        this.$target.remove();
        this.$el.remove();

        var node = $parent[0];
        if (node && node.firstChild) {
            if (!node.firstChild.tagName && node.firstChild.textContent === ' ') {
                node.removeChild(node.firstChild);
            }
        }

        if ($parent.closest(':data("snippet-editor")').length) {
            var editor = $parent.data('snippet-editor');
            while (!editor) {
                var $nextParent = $parent.parent();
                if (isEmptyAndRemovable($parent)) {
                    $parent.remove();
                }
                $parent = $nextParent;
                editor = $parent.data('snippet-editor');
            }
            if (isEmptyAndRemovable($parent, editor)) {
                setTimeout(() => editor.removeSnippet());
            }
        }

        // clean editor if they are image or table in deleted content
        this.$body.find('.note-control-selection').hide();
        this.$body.find('.o_table_handler').remove();

        this.trigger_up('snippet_removed');
        this.destroy();
        $parent.trigger('content_changed');

        function isEmptyAndRemovable($el, editor) {
            editor = editor || $el.data('snippet-editor');
            return $el.children().length === 0 && $el.text().trim() === ''
                && !$el.hasClass('oe_structure') && (!editor || editor.isTargetParentEditable);
        }
    },
    /**
     * Displays/Hides the editor overlay.
     *
     * @param {boolean} show
     * @param {boolean} [previewMode=false]
     */
    toggleOverlay: function (show, previewMode) {
        if (!this.$el) {
            return;
        }

        if (previewMode) {
            // In preview mode, the sticky classes are left untouched, we only
            // add/remove the preview class when toggling/untoggling
            this.$el.toggleClass('o_we_overlay_preview', show);
        } else {
            // In non preview mode, the preview class is always removed, and the
            // sticky class is added/removed when toggling/untoggling
            this.$el.removeClass('o_we_overlay_preview');
            this.$el.toggleClass('o_we_overlay_sticky', show);
        }

        show = this.$el.hasClass('o_we_overlay_sticky') ? true : show;

        // Show/hide overlay in preview mode or not
        this.$el.toggleClass('oe_active', show);
        this.cover();
    },
    /**
     * Displays/Hides the editor (+ parent) options and call onFocus/onBlur if
     * necessary.
     *
     * @param {boolean} show
     */
    toggleOptions: function (show) {
        if (!this.$el) {
            return;
        }

        if (this.areOptionsShown() === show) {
            return;
        }
        this.trigger_up('update_customize_elements', {
            customize$Elements: show ? this._customize$Elements : [],
        });
        this._customize$Elements.forEach(($el, i) => {
            var editor = $el.data('editor');
            var styles = _.values(editor.styles);
            _.sortBy(styles, '__order').forEach(style => {
                if (show) {
                    style.onFocus();
                    style.updateUI();
                } else {
                    style.onBlur();
                }
            });
        });
    },
    /**
     * @param {boolean} [show]
     * @returns {Promise<boolean>}
     */
    toggleTargetVisibility: async function (show) {
        show = this._toggleVisibilityStatus(show);
        var styles = _.values(this.styles);
        const proms = _.sortBy(styles, '__order').map(style => {
            return show ? style.onTargetShow() : style.onTargetHide();
        });
        await Promise.all(proms);
        return show;
    },
    /**
     * @param {boolean} [isTextEdition=false]
     */
    toggleTextEdition: function (isTextEdition) {
        if (this.$el) {
            this.$el.toggleClass('o_keypress', !!isTextEdition && this.isShown());
        }
    },
    /**
     * Clones the current snippet.
     *
     * @private
     * @param {boolean} recordUndo
     */
    clone: function (recordUndo) {
        this.trigger_up('snippet_will_be_cloned', {$target: this.$target});

        var $clone = this.$target.clone(false);

        if (recordUndo) {
            this.trigger_up('request_history_undo_record', {$target: this.$target});
        }

        this.$target.after($clone);
        this.trigger_up('call_for_each_child_snippet', {
            $snippet: $clone,
            callback: function (editor, $snippet) {
                for (var i in editor.styles) {
                    editor.styles[i].onClone({
                        isCurrent: ($snippet.is($clone)),
                    });
                }
            },
        });
        this.trigger_up('snippet_cloned', {$target: $clone, $origin: this.$target});

        $clone.trigger('content_changed');
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Instantiates the snippet's options.
     *
     * @private
     */
    _initializeOptions: function () {
        this._customize$Elements = [];
        this.styles = {};
        this.selectorSiblings = [];
        this.selectorChildren = [];

        var $element = this.$target.parent();
        while ($element.length) {
            var parentEditor = $element.data('snippet-editor');
            if (parentEditor) {
                this._customize$Elements = this._customize$Elements
                    .concat(parentEditor._customize$Elements);
                break;
            }
            $element = $element.parent();
        }

        var $optionsSection = $(core.qweb.render('web_editor.customize_block_options_section', {
            name: this.getName(),
        })).data('editor', this);
        const $optionsSectionBtnGroup = $optionsSection.find('we-button-group');
        $optionsSectionBtnGroup.contents().each((i, node) => {
            if (node.nodeType === Node.TEXT_NODE) {
                node.parentNode.removeChild(node);
            }
        });
        $optionsSection.on('mouseover', this._onOptionsSectionMouseOver.bind(this));
        $optionsSection.on('mouseleave', this._onOptionsSectionMouseLeave.bind(this));
        $optionsSection.on('click', 'we-title > span', this._onOptionsSectionClick.bind(this));
        $optionsSection.on('click', '.oe_snippet_clone', this._onCloneClick.bind(this));
        $optionsSection.on('click', '.oe_snippet_remove', this._onRemoveClick.bind(this));
        this._customize$Elements.push($optionsSection);

        // TODO get rid of this when possible (made as a fix to support old
        // theme options)
        this.$el.data('$optionsSection', $optionsSection);

        var i = 0;
        var defs = _.map(this.templateOptions, val => {
            if (!val.selector.is(this.$target)) {
                return;
            }
            if (val['drop-near']) {
                this.selectorSiblings.push(val['drop-near']);
            }
            if (val['drop-in']) {
                this.selectorChildren.push(val['drop-in']);
            }

            var optionName = val.option;
            var option = new (options.registry[optionName] || options.Class)(
                this,
                val.$el.children(),
                val.base_target ? this.$target.find(val.base_target).eq(0) : this.$target,
                this.$el,
                _.extend({
                    optionName: optionName,
                    snippetName: this.getName(),
                }, val.data),
                this.options
            );
            var key = optionName || _.uniqueId('option');
            if (this.styles[key]) {
                // If two snippet options use the same option name (and so use
                // the same JS option), store the subsequent ones with a unique
                // ID (TODO improve)
                key = _.uniqueId(key);
            }
            this.styles[key] = option;
            option.__order = i++;
            return option.appendTo(document.createDocumentFragment());
        });

        this.isTargetMovable = (this.selectorSiblings.length > 0 || this.selectorChildren.length > 0);

        this.$el.find('[data-toggle="dropdown"]').dropdown();

        return Promise.all(defs).then(() => {
            const options = _.sortBy(this.styles, '__order');
            options.forEach(option => {
                if (option.isTopOption) {
                    $optionsSectionBtnGroup.prepend(option.$el);
                } else {
                    $optionsSection.append(option.$el);
                }
            });
            $optionsSection.toggleClass('d-none', options.length === 0);
        });
    },
    /**
     * @private
     * @param {boolean} [show]
     */
    _toggleVisibilityStatus: function (show) {
        if (show === undefined) {
            show = !this.isTargetVisible();
        }
        if (show) {
            delete this.$target[0].dataset.invisible;
        } else {
            this.$target[0].dataset.invisible = '1';
        }
        return show;
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Called when the 'clone' button is clicked.
     *
     * @private
     * @param {Event} ev
     */
    _onCloneClick: function (ev) {
        ev.preventDefault();
        this.clone(true);
    },
    /**
     * Called when the snippet is starting to be dragged thanks to the 'move'
     * button.
     *
     * @private
     */
    _onDragAndDropStart: function () {
        var self = this;
        this.dropped = false;
        self.size = {
            width: self.$target.width(),
            height: self.$target.height()
        };
        self.$target.after('<div class="oe_drop_clone" style="display: none;"/>');
        self.$target.detach();
        self.$el.addClass('d-none');

        var $selectorSiblings;
        for (var i = 0; i < self.selectorSiblings.length; i++) {
            if (!$selectorSiblings) {
                $selectorSiblings = self.selectorSiblings[i].all();
            } else {
                $selectorSiblings = $selectorSiblings.add(self.selectorSiblings[i].all());
            }
        }
        var $selectorChildren;
        for (i = 0; i < self.selectorChildren.length; i++) {
            if (!$selectorChildren) {
                $selectorChildren = self.selectorChildren[i].all();
            } else {
                $selectorChildren = $selectorChildren.add(self.selectorChildren[i].all());
            }
        }

        this.trigger_up('go_to_parent', {$snippet: this.$target});
        this.trigger_up('activate_insertion_zones', {
            $selectorSiblings: $selectorSiblings,
            $selectorChildren: $selectorChildren,
        });

        this.$body.addClass('move-important');

        this.$editable.find('.oe_drop_zone').droppable({
            over: function () {
                self.$editable.find('.oe_drop_zone.hide').removeClass('hide');
                $(this).addClass('hide').first().after(self.$target);
                self.dropped = true;
            },
            out: function () {
                $(this).removeClass('hide');
                self.$target.detach();
                self.dropped = false;
            },
        });
    },
    /**
     * Called when the snippet is dropped after being dragged thanks to the
     * 'move' button.
     *
     * @private
     * @param {Event} ev
     * @param {Object} ui
     */
    _onDragAndDropStop: function (ev, ui) {
        // TODO lot of this is duplicated code of the d&d feature of snippets
        if (!this.dropped) {
            var $el = $.nearest({x: ui.position.left, y: ui.position.top}, '.oe_drop_zone', {container: document.body}).first();
            if ($el.length) {
                $el.after(this.$target);
                this.dropped = true;
            }
        }

        this.$editable.find('.oe_drop_zone').droppable('destroy').remove();

        var prev = this.$target.first()[0].previousSibling;
        var next = this.$target.last()[0].nextSibling;
        var $parent = this.$target.parent();

        var $clone = this.$editable.find('.oe_drop_clone');
        if (prev === $clone[0]) {
            prev = $clone[0].previousSibling;
        } else if (next === $clone[0]) {
            next = $clone[0].nextSibling;
        }
        $clone.after(this.$target);
        var $from = $clone.parent();

        this.$el.removeClass('d-none');
        this.$body.removeClass('move-important');
        $clone.remove();

        if (this.dropped) {
            this.trigger_up('request_history_undo_record', {$target: this.$target});

            if (prev) {
                this.$target.insertAfter(prev);
            } else if (next) {
                this.$target.insertBefore(next);
            } else {
                $parent.prepend(this.$target);
            }

            for (var i in this.styles) {
                this.styles[i].onMove();
            }

            this.$target.trigger('content_changed');
            $from.trigger('content_changed');
        }

        this.trigger_up('drag_and_drop_stop', {
            $snippet: this.$target,
        });
    },
    /**
     * @private
     */
    _onOptionsSectionMouseOver: function (ev) {
        this.trigger_up('activate_snippet', {
            $snippet: this.$target,
            previewMode: true,
        });
    },
    /**
     * @private
     */
    _onOptionsSectionMouseLeave: function (ev) {
        this.trigger_up('activate_snippet', {
            $snippet: false,
            previewMode: true,
        });
    },
    /**
     * @private
     */
    _onOptionsSectionClick: function (ev) {
        this.trigger_up('activate_snippet', {
            $snippet: this.$target,
            previewMode: false,
        });
    },
    /**
     * Called when a child editor/option asks for another option to perform a
     * specific action/react to a specific event.
     *
     * @private
     * @param {OdooEvent} ev
     */
    _onOptionUpdate: function (ev) {
        var self = this;

        // If multiple option names are given, we suppose it should not be
        // propagated to parent editor
        if (ev.data.optionNames) {
            ev.stopPropagation();
            _.each(ev.data.optionNames, function (name) {
                notifyForEachMatchedOption(name);
            });
        }
        // If one option name is given, we suppose it should be handle by the
        // first parent editor which can do it
        if (ev.data.optionName) {
            if (notifyForEachMatchedOption(ev.data.optionName)) {
                ev.stopPropagation();
            }
        }

        function notifyForEachMatchedOption(name) {
            var regex = new RegExp('^' + name + '\\d+$');
            var hasOption = false;
            for (var key in self.styles) {
                if (key === name || regex.test(key)) {
                    self.styles[key].notify(ev.data.name, ev.data.data);
                    hasOption = true;
                }
            }
            return hasOption;
        }
    },
    /**
     * Called when the 'remove' button is clicked.
     *
     * @private
     * @param {Event} ev
     */
    _onRemoveClick: function (ev) {
        ev.preventDefault();
        ev.stopPropagation();
        this.trigger_up('request_history_undo_record', {$target: this.$target});
        this.removeSnippet();
    },
    /**
     * @private
     * @param {OdooEvent} ev
     */
    _onSnippetOptionUpdate: async function (ev) {
        if (ev.data.previewMode) {
            ev.data.onSuccess();
            return;
        }

        const proms1 = Object.keys(this.styles).map(key => {
            return this.styles[key].updateUI({
                forced: ev.data.widget,
                noVisibility: true,
            });
        });
        await Promise.all(proms1);

        const proms2 = Object.keys(this.styles).map(key => {
            return this.styles[key].updateUIVisibility();
        });
        await Promise.all(proms2);

        ev.data.onSuccess();
    },
    /**
     * @private
     * @param {OdooEvent} ev
     */
    _onSnippetOptionVisibilityUpdate: function (ev) {
        ev.data.show = this._toggleVisibilityStatus(ev.data.show);
    },
    /**
     * @private
     * @param {Event} ev
     */
    _onUserValueWidgetRequest: function (ev) {
        for (const key of Object.keys(this.styles)) {
            const widget = this.styles[key].findWidget(ev.data.name);
            if (widget) {
                ev.data.onSuccess(widget);
                return;
            }
        }
    },
});

/**
 * Management of drag&drop menu and snippet related behaviors in the page.
 */
var SnippetsMenu = Widget.extend({
    id: 'oe_snippets',
    cacheSnippetTemplate: {},
    events: {
        'click .o_install_btn': '_onInstallBtnClick',
        'click .o_we_invisible_entry': '_onInvisibleEntryClick',
    },
    custom_events: {
        'activate_insertion_zones': '_onActivateInsertionZones',
        'activate_snippet': '_onActivateSnippet',
        'call_for_each_child_snippet': '_onCallForEachChildSnippet',
        'clone_snippet': '_onCloneSnippet',
        'cover_update': '_onOverlaysCoverUpdate',
        'deactivate_snippet': '_onDeactivateSnippet',
        'drag_and_drop_stop': '_onDragAndDropStop',
        'go_to_parent': '_onGoToParent',
        'remove_snippet': '_onRemoveSnippet',
        'snippet_edition_request': '_onSnippetEditionRequest',
        'snippet_removed': '_onSnippetRemoved',
        'snippet_cloned': '_onSnippetCloned',
        'snippet_option_visibility_update': '_onSnippetOptionVisibilityUpdate',
        'reload_snippet_dropzones': '_disableUndroppableSnippets',
        'update_customize_elements': '_onUpdateCustomizeElements',
        'hide_overlay': '_onHideOverlay',
        'block_preview_overlays': '_onBlockPreviewOverlays',
        'unblock_preview_overlays': '_onUnblockPreviewOverlays',
        'user_value_widget_opening': '_onUserValueWidgetOpening',
    },

    /**
     * @param {Widget} parent
     * @param {Object} [options]
     * @param {string} [options.snippets]
     *      URL of the snippets template. This URL might have been set
     *      in the global 'snippets' variable, otherwise this function
     *      assigns a default one.
     *      default: 'web_editor.snippets'
     *
     * @constructor
     */
    init: function (parent, options) {
        this._super.apply(this, arguments);
        options = options || {};
        this.trigger_up('getRecordInfo', {
            recordInfo: options,
            callback: function (recordInfo) {
                _.defaults(options, recordInfo);
            },
        });

        this.options = options;
        if (!this.options.snippets) {
            this.options.snippets = 'web_editor.snippets';
        }
        this.snippetEditors = [];
        this._enabledEditorHierarchy = [];

        this._mutex = new concurrency.Mutex();

        this.setSelectorEditableArea(options.$el, options.selectorEditableArea);

        this._notActivableElementsSelector = [
            '#web_editor-top-edit',
            '#oe_snippets',
            '#oe_manipulators',
            '.o_technical_modal',
            '.oe_drop_zone',
            '.o_notification_manager',
            '.o_we_no_overlay',
            '.ui-autocomplete',
            '.modal .close',
        ].join(', ');
    },
    /**
     * @override
     */
    start: function () {
        var defs = [this._super.apply(this, arguments)];
        this.ownerDocument = this.$el[0].ownerDocument;
        this.$document = $(this.ownerDocument);
        this.window = this.ownerDocument.defaultView;
        this.$window = $(this.window);

        // Fetch snippet templates and compute it

        defs.push(this.loadSnippets().then(html => {
            return this._computeSnippetTemplates(html);
        }).then(() => {
            this.customizePanel = document.createElement('div');
            this.customizePanel.classList.add('o_we_customize_panel', 'd-none');
            this.$el.append(this.customizePanel);

            this.invisibleDOMPanelEl = document.createElement('div');
            this.invisibleDOMPanelEl.classList.add('o_we_invisible_el_panel');
            this.invisibleDOMPanelEl.appendChild(
                $('<div/>', {
                    text: _t('Invisible Elements'),
                    class: 'o_panel_header',
                }).prepend(
                    $('<i/>', {class: 'fa fa-eye-slash'})
                )[0]
            );
            this.$el.append(this.invisibleDOMPanelEl);
            return this._updateInvisibleDOM();
        }));

        // Prepare snippets editor environment
        this.$snippetEditorArea = $('<div/>', {
            id: 'oe_manipulators',
        }).insertAfter(this.$el);

        // Active snippet editor on click in the page
        var lastElement;
        this.$document.on('click.snippets_menu', '*', ev => {
            var srcElement = ev.target || (ev.originalEvent && (ev.originalEvent.target || ev.originalEvent.originalTarget)) || ev.srcElement;
            if (!srcElement || lastElement === srcElement) {
                return;
            }
            lastElement = srcElement;
            _.defer(function () {
                lastElement = false;
            });

            var $target = $(srcElement);
            if ($target.closest('#snippets_menu').length) {
                this._activateSnippet(false);
                return;
            }
            if (!$target.closest('body > *').length) {
                return;
            }
            if ($target.closest(this._notActivableElementsSelector).length) {
                return;
            }
            this._activateSnippet($target);
        });

        core.bus.on('deactivate_snippet', this, this._onDeactivateSnippet);

        // Adapt overlay covering when the window is resized / content changes
        var debouncedCoverUpdate = _.throttle(() => {
            this.updateCurrentSnippetEditorOverlay();
        }, 50);
        this.$window.on('resize.snippets_menu', debouncedCoverUpdate);
        this.$window.on('content_changed.snippets_menu', debouncedCoverUpdate);

        // On keydown add a class on the active overlay to hide it and show it
        // again when the mouse moves
        this.$document.on('keydown.snippets_menu', () => {
            this.snippetEditors.forEach(editor => {
                editor.toggleTextEdition(true);
            });
        });
        this.$document.on('mousemove.snippets_menu, mousedown.snippets_menu', () => {
            this.snippetEditors.forEach(editor => {
                editor.toggleTextEdition(false);
            });
        });

        // Auto-selects text elements with a specific class and remove this
        // on text changes
        this.$document.on('click.snippets_menu', '.o_default_snippet_text', function (ev) {
            $(ev.target).closest('.o_default_snippet_text').removeClass('o_default_snippet_text');
            $(ev.target).selectContent();
            $(ev.target).removeClass('o_default_snippet_text');
        });
        this.$document.on('keyup.snippets_menu', function () {
            var range = Wysiwyg.getRange(this);
            $(range && range.sc).closest('.o_default_snippet_text').removeClass('o_default_snippet_text');
        });

        return Promise.all(defs).then(() => {
            this.$('[data-title]').tooltip({
                delay: 0,
                title: function () {
                    return this.classList.contains('active') ? false : this.dataset.title;
                },
            });

            // Trigger a resize event once entering edit mode as the snippets
            // menu will take part of the screen width (delayed because of
            // animation). (TODO wait for real animation end)
            setTimeout(() => {
                this.$window.trigger('resize');
            }, 1000);
        });
    },
    /**
     * @override
     */
    destroy: function () {
        this._super.apply(this, arguments);
        if (this.$window) {
            this.$snippetEditorArea.remove();
            this.$window.off('.snippets_menu');
            this.$document.off('.snippets_menu');
        }
        core.bus.off('deactivate_snippet', this, this._onDeactivateSnippet);
        delete this.cacheSnippetTemplate[this.options.snippets];
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Prepares the page so that it may be saved:
     * - Asks the snippet editors to clean their associated snippet
     * - Remove the 'contentEditable' attributes
     */
    cleanForSave: async function () {
        await this._activateSnippet(false);
        this.trigger_up('ready_to_clean_for_save');
        await this._destroyEditors();

        this.getEditableArea().find('[contentEditable]')
            .removeAttr('contentEditable')
            .removeProp('contentEditable');

        this.getEditableArea().find('.o_we_selected_image')
            .removeClass('o_we_selected_image');
    },
    /**
     * Load snippets.
     */
    loadSnippets: function () {
        if (this.cacheSnippetTemplate[this.options.snippets]) {
            this._defLoadSnippets = this.cacheSnippetTemplate[this.options.snippets];
            return this._defLoadSnippets;
        }
        this._defLoadSnippets = this._rpc({
            model: 'ir.ui.view',
            method: 'render_template',
            args: [this.options.snippets, {}],
            kwargs: {
                context: this.options.context,
            },
        });
        this.cacheSnippetTemplate[this.options.snippets] = this._defLoadSnippets;
        return this._defLoadSnippets;
    },
    /**
     * Sets the instance variables $editor, $body and selectorEditableArea.
     *
     * @param {JQuery} $editor
     * @param {String} selectorEditableArea
     */
    setSelectorEditableArea: function ($editor, selectorEditableArea) {
        this.selectorEditableArea = selectorEditableArea;
        this.$editor = $editor;
        this.$body = $editor.closest('body');
    },
    /**
     * Get the editable area.
     *
     * @returns {JQuery}
     */
    getEditableArea: function () {
        return this.$editor.find(this.selectorEditableArea)
            .add(this.$editor.filter(this.selectorEditableArea));
    },
    /**
     * Updates the cover dimensions of the current snippet editor.
     */
    updateCurrentSnippetEditorOverlay: function () {
        this.snippetEditors = _.filter(this.snippetEditors, function (snippetEditor) {
            if (snippetEditor.$target.closest('body').length) {
                snippetEditor.cover();
                return true;
            }
            snippetEditor.destroy();
        });
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Creates drop zones in the DOM (locations where snippets may be dropped).
     * Those locations are determined thanks to the two types of given DOM.
     *
     * @private
     * @param {jQuery} [$selectorSiblings]
     *        elements which must have siblings drop zones
     * @param {jQuery} [$selectorChildren]
     *        elements which must have child drop zones between each of existing
     *        child
     */
    _activateInsertionZones: function ($selectorSiblings, $selectorChildren) {
        var self = this;

        function isFullWidth($elem) {
            return $elem.parent().width() === $elem.outerWidth(true);
        }

        if ($selectorChildren) {
            $selectorChildren.each(function () {
                var $zone = $(this);
                var style;
                var vertical;
                var node;
                var css = self.window.getComputedStyle(this);
                var parentCss = self.window.getComputedStyle($zone.parent()[0]);
                var float = css.float || css.cssFloat;
                var parentDisplay = parentCss.display;
                var parentFlex = parentCss.flexDirection;

                style = {};
                vertical = false;
                node = $zone[0].lastChild;
                var test = !!(node && ((!node.tagName && node.textContent.match(/\S/)) || node.tagName === 'BR'));
                if (test) {
                    vertical = true;
                    style['float'] = 'none';
                    style['height'] = parseInt(self.window.getComputedStyle($zone[0]).lineHeight) + 'px';
                    style['display'] = 'inline-block';
                } else if (float === 'left' || float === 'right' || (parentDisplay === 'flex' && parentFlex === 'row')) {
                    style['float'] = float;
                    if (!isFullWidth($zone)) {
                        vertical = true;
                        style['height'] = Math.max($zone.outerHeight(), 30) + 'px';
                    }
                }
                self._insertDropzone($('<we-hook/>').appendTo($zone), vertical, style);

                style = {};
                vertical = false;
                node = $zone[0].firstChild;
                test = !!(node && ((!node.tagName && node.textContent.match(/\S/)) || node.tagName === 'BR'));
                if (test) {
                    vertical = true;
                    style['float'] = 'none';
                    style['height'] = parseInt(self.window.getComputedStyle($zone[0]).lineHeight) + 'px';
                    style['display'] = 'inline-block';
                } else if (float === 'left' || float === 'right' || (parentDisplay === 'flex' && parentFlex === 'row')) {
                    style['float'] = float;
                    if (!isFullWidth($zone)) {
                        vertical = true;
                        style['height'] = Math.max($zone.outerHeight(), 30) + 'px';
                    }
                }
                self._insertDropzone($('<we-hook/>').prependTo($zone), vertical, style);
            });

            // add children near drop zone
            $selectorSiblings = $(_.uniq(($selectorSiblings || $()).add($selectorChildren.children()).get()));
        }

        if ($selectorSiblings) {
            $selectorSiblings.filter(':not(.oe_drop_zone):not(.oe_drop_clone)').each(function () {
                var $zone = $(this);
                var style;
                var vertical;
                var css = self.window.getComputedStyle(this);
                var parentCss = self.window.getComputedStyle($zone.parent()[0]);
                var float = css.float || css.cssFloat;
                var parentDisplay = parentCss.display;
                var parentFlex = parentCss.flexDirection;

                if ($zone.prev('.oe_drop_zone:visible').length === 0) {
                    style = {};
                    vertical = false;
                    if (float === 'left' || float === 'right' || (parentDisplay === 'flex' && parentFlex === 'row')) {
                        style['float'] = float;
                        if (!isFullWidth($zone)) {
                            vertical = true;
                            style['height'] = Math.max($zone.outerHeight(), 30) + 'px';
                        }
                    }
                    self._insertDropzone($('<we-hook/>').insertBefore($zone), vertical, style);
                }
                if ($zone.next('.oe_drop_zone:visible').length === 0) {
                    style = {};
                    vertical = false;
                    if (float === 'left' || float === 'right' || (parentDisplay === 'flex' && parentFlex === 'row')) {
                        style['float'] = float;
                        if (!isFullWidth($zone)) {
                            vertical = true;
                            style['height'] = Math.max($zone.outerHeight(), 30) + 'px';
                        }
                    }
                    self._insertDropzone($('<we-hook/>').insertAfter($zone), vertical, style);
                }
            });
        }

        var count;
        var $zones;
        do {
            count = 0;
            $zones = this.getEditableArea().find('.oe_drop_zone > .oe_drop_zone').remove(); // no recursive zones
            count += $zones.length;
            $zones.remove();
        } while (count > 0);

        // Cleaning consecutive zone and up zones placed between floating or
        // inline elements. We do not like these kind of zones.
        $zones = this.getEditableArea().find('.oe_drop_zone:not(.oe_vertical)');
        $zones.each(function () {
            var zone = $(this);
            var prev = zone.prev();
            var next = zone.next();
            // remove consecutive zone
            if (prev.is('.oe_drop_zone') || next.is('.oe_drop_zone')) {
                zone.remove();
                return;
            }
            var floatPrev = prev.css('float') || 'none';
            var floatNext = next.css('float') || 'none';
            var dispPrev = prev.css('display') || null;
            var dispNext = next.css('display') || null;
            if ((floatPrev === 'left' || floatPrev === 'right')
             && (floatNext === 'left' || floatNext === 'right')) {
                zone.remove();
            } else if (dispPrev !== null && dispNext !== null
             && dispPrev.indexOf('inline') >= 0 && dispNext.indexOf('inline') >= 0) {
                zone.remove();
            }
        });
    },
    /**
     * Adds an entry for every invisible snippet in the left panel box.
     * The entries will contains an 'Edit' button to activate their snippet.
     *
     * @private
     * @returns {Promise}
     */
    _updateInvisibleDOM: function () {
        return this._mutex.exec(() => {
            this.invisibleDOMMap = new Map();
            const $invisibleDOMPanelEl = $(this.invisibleDOMPanelEl);
            $invisibleDOMPanelEl.find('.o_we_invisible_entry').remove();
            const $invisibleSnippets = this.getEditableArea().find('.o_snippet_invisible');

            $invisibleDOMPanelEl.toggleClass('d-none', !$invisibleSnippets.length);

            const proms = _.map($invisibleSnippets, async el => {
                const editor = await this._createSnippetEditor($(el));
                const $invisEntry = $('<div/>', {
                    class: 'o_we_invisible_entry d-flex align-items-center justify-content-between',
                    text: editor.getName(),
                }).append($('<i/>', {class: `fa ${editor.isTargetVisible() ? 'fa-eye' : 'fa-eye-slash'} ml-2`}));
                $invisibleDOMPanelEl.append($invisEntry);
                this.invisibleDOMMap.set($invisEntry[0], el);
            });
            return Promise.all(proms);
        });
    },
    /**
     * Disable the overlay editor of the active snippet and activate the new one
     * if given.
     * Note 1: if the snippet editor associated to the given snippet is not
     *         created yet, this method will create it.
     * Note 2: if the given DOM element is not a snippet (no editor option), the
     *         first parent which is one is used instead.
     *
     * @param {jQuery|false} $snippet
     *        The DOM element whose editor (and its parent ones) need to be
     *        enabled. Only disable the current one if false is given.
     * @param {boolean} [previewMode=false]
     * @param {boolean} [ifInactiveOptions=false]
     * @returns {Promise<SnippetEditor>}
     *          (might be async when an editor must be created)
     */
    _activateSnippet: function ($snippet, previewMode, ifInactiveOptions) {
        if (this._blockPreviewOverlays && previewMode) {
            return Promise.resolve();
        }
        return this._mutex.exec(() => {
            return new Promise(resolve => {
                // Take the first parent of the provided DOM (or itself) which
                // should have an associated snippet editor and create + enable it.
                if ($snippet && $snippet.length) {
                    $snippet = globalSelector.closest($snippet);
                    if ($snippet.length) {
                        return this._createSnippetEditor($snippet).then(resolve);
                    }
                }
                resolve(null);
            }).then(editorToEnable => {
                if (ifInactiveOptions && this._enabledEditorHierarchy.includes(editorToEnable)) {
                    return editorToEnable;
                }

                const editorToEnableHierarchy = [];
                let current = editorToEnable;
                while (current && current.$target) {
                    editorToEnableHierarchy.push(current);
                    current = current.getParent();
                }

                // First disable all editors...
                for (let i = this.snippetEditors.length; i--;) {
                    const editor = this.snippetEditors[i];
                    editor.toggleOverlay(false, previewMode);
                    if (!previewMode && !editorToEnableHierarchy.includes(editor)) {
                        editor.toggleOptions(false);
                    }
                }
                // ... then enable the right editor
                if (editorToEnable) {
                    editorToEnable.toggleOverlay(true, previewMode);
                    editorToEnable.toggleOptions(true);
                }

                this._enabledEditorHierarchy = editorToEnableHierarchy;
                return editorToEnable;
            });
        });
    },
    /**
     * @private
     */
    _destroyEditors: async function () {
        const proms = _.map(this.snippetEditors, async function (snippetEditor) {
            await snippetEditor.cleanForSave();
            snippetEditor.destroy();
        });
        await Promise.all(proms);
        this.snippetEditors.splice(0);
    },
    /**
     * Calls a given callback 'on' the given snippet and all its child ones if
     * any (DOM element with options).
     *
     * Note: the method creates the snippet editors if they do not exist yet.
     *
     * @private
     * @param {jQuery} $snippet
     * @param {function} callback
     *        Given two arguments: the snippet editor associated to the snippet
     *        being managed and the DOM element of this snippet.
     * @returns {Promise} (might be async if snippet editors need to be created
     *                     and/or the callback is async)
     */
    _callForEachChildSnippet: function ($snippet, callback) {
        var self = this;
        var defs = _.map($snippet.add(globalSelector.all($snippet)), function (el) {
            var $snippet = $(el);
            return self._createSnippetEditor($snippet).then(function (editor) {
                if (editor) {
                    return callback.call(self, editor, $snippet);
                }
            });
        });
        return Promise.all(defs);
    },
    /**
     * @private
     */
    _closeWidgets: function () {
        this.snippetEditors.forEach(editor => editor.closeWidgets());
    },
    /**
     * Creates and returns a set of helper functions which can help finding
     * snippets in the DOM which match some parameters (typically parameters
     * given by a snippet option). The functions are:
     *
     * - `is`: to determine if a given DOM is a snippet that matches the
     *         parameters
     *
     * - `closest`: find closest parent (or itself) of a given DOM which is a
     *              snippet that matches the parameters
     *
     * - `all`: find all snippets in the DOM that match the parameters
     *
     * See implementation for function details.
     *
     * @private
     * @param {string} include
     *        jQuery selector that DOM elements must match to be considered as
     *        potential snippet.
     * @param {string} exclude
     *        jQuery selector that DOM elements must *not* match the be
     *        considered as potential snippet.
     * @param {string|false} target
     *        jQuery selector that at least one child of a DOM element must
     *        match to that DOM element be considered as a potential snippet.
     * @param {boolean} noCheck
     *        true if DOM elements which are technically not in an editable
     *        environment may be considered.
     * @param {boolean} isChildren
     *        when the DOM elements must be in an editable environment to be
     *        considered (@see noCheck), this is true if the DOM elements'
     *        parent must also be in an editable environment to be considered.
     */
    _computeSelectorFunctions: function (include, exclude, target, noCheck, isChildren) {
        var self = this;

        // Convert the selector for elements to include into a list
        var selectorList = _.compact(include.split(/\s*,\s*/));

        // Convert the selector for elements to exclude into a list
        var excludeList = _.compact(exclude.split(/\s*,\s*/));
        excludeList.push('.o_snippet_not_selectable');

        // Prepare the condition that will be added to each subselector for
        // elements to include: 'not the elements to exclude and only the
        // editable ones if needed'
        var selectorConditions = _.map(excludeList, function (exc) {
            return ':not(' + exc + ')';
        }).join('');
        if (target) {
            selectorConditions += ':has(' + target + ')';
        }
        if (!noCheck) {
            selectorConditions = (this.options.addDropSelector || '') + selectorConditions;
        }

        // (Re)join the subselectors
        var selector = _.map(selectorList, function (s) {
            return s + selectorConditions;
        }).join(', ');

        // Prepare the functions
        var functions = {
            is: function ($from) {
                return $from.is(selector);
            },
        };
        if (noCheck) {
            functions.closest = function ($from, parentNode) {
                return $from.closest(selector, parentNode);
            };
            functions.all = function ($from) {
                return $from ? dom.cssFind($from, selector) : $(selector);
            };
        } else {
            functions.closest = function ($from, parentNode) {
                var parents = self.getEditableArea().get();
                return $from.closest(selector, parentNode).filter(function () {
                    var node = this;
                    while (node.parentNode) {
                        if (parents.indexOf(node) !== -1) {
                            return true;
                        }
                        node = node.parentNode;
                    }
                    return false;
                });
            };
            functions.all = isChildren ? function ($from) {
                return dom.cssFind($from || self.getEditableArea(), selector);
            } : function ($from) {
                $from = $from || self.getEditableArea();
                return $from.filter(selector).add(dom.cssFind($from, selector));
            };
        }
        return functions;
    },
    /**
     * Processes the given snippet template to register snippet options, creates
     * draggable thumbnail, etc.
     *
     * @private
     * @param {string} html
     */
    _computeSnippetTemplates: function (html) {
        var self = this;
        var $html = $(html);
        var $scroll = $html.siblings('#o_scroll');

        $html.find('[data-oe-type="snippet"]').each(function () {
            $(this).children()
                .attr('data-oe-type', 'snippet')
                .attr('data-oe-thumbnail', $(this).data('oe-thumbnail'));
        });

        this.templateOptions = [];
        var selectors = [];
        var $styles = $html.find('[data-selector]');
        $styles.each(function () {
            var $style = $(this);
            var selector = $style.data('selector');
            var exclude = $style.data('exclude') || '';
            var target = $style.data('target');
            var noCheck = $style.data('no-check');
            var optionID = $style.data('js');
            var option = {
                'option': optionID,
                'base_selector': selector,
                'base_exclude': exclude,
                'base_target': target,
                'selector': self._computeSelectorFunctions(selector, exclude, target, noCheck),
                '$el': $style,
                'drop-near': $style.data('drop-near') && self._computeSelectorFunctions($style.data('drop-near'), '', false, noCheck, true),
                'drop-in': $style.data('drop-in') && self._computeSelectorFunctions($style.data('drop-in'), '', false, noCheck),
                'data': _.extend({string: $style.attr('string')}, $style.data()),
            };
            self.templateOptions.push(option);
            selectors.push(option.selector);
        });
        $styles.addClass('d-none');

        globalSelector.closest = function ($from) {
            var $temp;
            var $target;
            for (var i = 0, len = selectors.length; i < len; i++) {
                $temp = selectors[i].closest($from, $target && $target[0]);
                if ($temp.length) {
                    $target = $temp;
                }
            }
            return $target || $();
        };
        globalSelector.all = function ($from) {
            var $target = $();
            for (var i = 0, len = selectors.length; i < len; i++) {
                $target = $target.add(selectors[i].all($from));
            }
            return $target;
        };
        globalSelector.is = function ($from) {
            for (var i = 0, len = selectors.length; i < len; i++) {
                if (selectors[i].is($from)) {
                    return true;
                }
            }
            return false;
        };

        this.$snippets = $scroll.find('.o_panel_body').children()
            .addClass('oe_snippet')
            .each(function () {
                var $snippet = $(this);
                var name = $snippet.attr('name');
                var $sbody = $snippet.children(':not(.oe_snippet_thumbnail)').addClass('oe_snippet_body');

                // Associate in-page snippets to their name
                if ($sbody.length) {
                    var snippetClasses = $sbody.attr('class').match(/s_[^ ]+/g);
                    if (snippetClasses && snippetClasses.length) {
                        snippetClasses = '.' + snippetClasses.join('.');
                    }
                    var $els = $(snippetClasses).not('[data-name]').add($sbody);
                    $els.attr('data-name', name).data('name', name);
                }

                // Create the thumbnail
                if ($snippet.find('.oe_snippet_thumbnail').length) {
                    return; // Compatibility with elements which do not use 't-snippet'
                }
                var $thumbnail = $(_.str.sprintf(
                    '<div class="oe_snippet_thumbnail">' +
                        '<div class="oe_snippet_thumbnail_img" style="background-image: url(%s);"/>' +
                        '<span class="oe_snippet_thumbnail_title">%s</span>' +
                    '</div>',
                    $snippet.find('[data-oe-thumbnail]').data('oeThumbnail'),
                    name
                ));
                $snippet.prepend($thumbnail);

                // Create the install button (t-install feature) if necessary
                var moduleID = $snippet.data('moduleId');
                if (moduleID) {
                    $snippet.addClass('o_snippet_install');
                    $thumbnail.append($('<button/>', {
                        class: 'btn btn-primary o_install_btn w-100',
                        type: 'button',
                        text: _t("Install"),
                    }));
                }
            })
            .not('[data-module-id]');

        // Hide scroll if no snippets defined
        if (!this.$snippets.length) {
            this.$el.detach();
        }

        // Register the text nodes that needs to be auto-selected on click
        this._registerDefaultTexts();

        // Remove branding from template
        _.each($html.find('[data-oe-model], [data-oe-type]'), function (el) {
            for (var k = 0; k < el.attributes.length; k++) {
                if (el.attributes[k].name.indexOf('data-oe-') === 0) {
                    $(el).removeAttr(el.attributes[k].name);
                    k--;
                }
            }
        });

        // Force non editable part to contentEditable=false
        $html.find('.o_not_editable').attr('contentEditable', false);

        // Add the computed template and make elements draggable
        this.$el.html($html);
        this._makeSnippetDraggable(this.$snippets);
        this._disableUndroppableSnippets();

        this.$el.addClass('o_loaded');
        $('body.editor_enable').addClass('editor_has_snippets');
        this.trigger_up('snippets_loaded', self.$el);
    },
    /**
     * Creates a snippet editor to associated to the given snippet. If the given
     * snippet already has a linked snippet editor, the function only returns
     * that one.
     * The function also instantiates a snippet editor for all snippet parents
     * as a snippet editor must be able to display the parent snippet options.
     *
     * @private
     * @param {jQuery} $snippet
     * @returns {Promise<SnippetEditor>}
     */
    _createSnippetEditor: function ($snippet) {
        var self = this;
        var snippetEditor = $snippet.data('snippet-editor');
        if (snippetEditor) {
            return snippetEditor.__isStarted;
        }

        var def;
        var $parent = globalSelector.closest($snippet.parent());
        if ($parent.length) {
            def = this._createSnippetEditor($parent);
        }

        return Promise.resolve(def).then(function (parentEditor) {
            // When reaching this position, after the Promise resolution, the
            // snippet editor instance might have been created by another call
            // to _createSnippetEditor... the whole logic should be improved
            // to avoid doing this here.
            snippetEditor = $snippet.data('snippet-editor');
            if (snippetEditor) {
                return snippetEditor.__isStarted;
            }

            let editableArea = self.getEditableArea();
            snippetEditor = new SnippetEditor(parentEditor || self, $snippet, self.templateOptions, $snippet.closest('[data-oe-type="html"], .oe_structure').add(editableArea), self.options);
            self.snippetEditors.push(snippetEditor);
            return snippetEditor.appendTo(self.$snippetEditorArea);
        }).then(function () {
            return snippetEditor;
        });
    },
    /**
     * There may be no location where some snippets might be dropped. This mades
     * them appear disabled in the menu.
     *
     * @todo make them undraggable
     * @private
     */
    _disableUndroppableSnippets: function () {
        var self = this;
        var cache = {};
        this.$snippets.each(function () {
            var $snippet = $(this);
            var $snippetBody = $snippet.find('.oe_snippet_body');

            var check = false;
            _.each(self.templateOptions, function (option, k) {
                if (check || !($snippetBody.is(option.base_selector) && !$snippetBody.is(option.base_exclude))) {
                    return;
                }

                cache[k] = cache[k] || {
                    'drop-near': option['drop-near'] ? option['drop-near'].all().length : 0,
                    'drop-in': option['drop-in'] ? option['drop-in'].all().length : 0
                };
                check = (cache[k]['drop-near'] || cache[k]['drop-in']);
            });

            $snippet.toggleClass('o_disabled', !check);
        });
    },
    /**
     * Creates a dropzone element and inserts it by replacing the given jQuery
     * location. This allows to add data on the dropzone depending on the hook
     * environment.
     *
     * @private
     * @param {jQuery} $hook
     * @param {boolean} [vertical=false]
     * @param {Object} [style]
     */
    _insertDropzone: function ($hook, vertical, style) {
        var $dropzone = $('<div/>', {
            'class': 'oe_drop_zone oe_insert' + (vertical ? ' oe_vertical' : ''),
        });
        if (style) {
            $dropzone.css(style);
        }
        $hook.replaceWith($dropzone);
        return $dropzone;
    },
    /**
     * Make given snippets be draggable/droppable thanks to their thumbnail.
     *
     * @private
     * @param {jQuery} $snippets
     */
    _makeSnippetDraggable: function ($snippets) {
        var self = this;
        var $tumb = $snippets.find('.oe_snippet_thumbnail_img:first');
        var left = $tumb.outerWidth() / 2;
        var top = $tumb.outerHeight() / 2;
        var $toInsert, dropped, $snippet;

        $snippets.draggable({
            greedy: true,
            helper: 'clone',
            appendTo: this.$body,
            cursor: 'move',
            handle: '.oe_snippet_thumbnail',
            distance: 30,
            cursorAt: {
                left: left,
                top: top,
            },
            start: function () {
                dropped = false;
                $snippet = $(this);
                var $baseBody = $snippet.find('.oe_snippet_body');
                var $selectorSiblings = $();
                var $selectorChildren = $();
                var temp = self.templateOptions;
                for (var k in temp) {
                    if ($baseBody.is(temp[k].base_selector) && !$baseBody.is(temp[k].base_exclude)) {
                        if (temp[k]['drop-near']) {
                            $selectorSiblings = $selectorSiblings.add(temp[k]['drop-near'].all());
                        }
                        if (temp[k]['drop-in']) {
                            $selectorChildren = $selectorChildren.add(temp[k]['drop-in'].all());
                        }
                    }
                }

                $toInsert = $baseBody.clone();

                if (!$selectorSiblings.length && !$selectorChildren.length) {
                    console.warn($snippet.find('.oe_snippet_thumbnail_title').text() + " have not insert action: data-drop-near or data-drop-in");
                    return;
                }

                self._activateSnippet(false);
                self._activateInsertionZones($selectorSiblings, $selectorChildren);

                self.getEditableArea().find('.oe_drop_zone').droppable({
                    over: function () {
                        if (!dropped) {
                            dropped = true;
                            $(this).first().after($toInsert).addClass('d-none');
                            $toInsert.removeClass('oe_snippet_body');
                        }
                    },
                    out: function () {
                        var prev = $toInsert.prev();
                        if (this === prev[0]) {
                            dropped = false;
                            $toInsert.detach();
                            $(this).removeClass('d-none');
                            $toInsert.addClass('oe_snippet_body');
                        }
                    },
                });
            },
            stop: function (ev, ui) {
                $toInsert.removeClass('oe_snippet_body');

                if (!dropped && ui.position.top > 3 && ui.position.left + 50 > self.$el.outerWidth()) {
                    var $el = $.nearest({x: ui.position.left, y: ui.position.top}, '.oe_drop_zone', {container: document.body}).first();
                    if ($el.length) {
                        $el.after($toInsert);
                        dropped = true;
                    }
                }

                self.getEditableArea().find('.oe_drop_zone').droppable('destroy').remove();

                if (dropped) {
                    var prev = $toInsert.first()[0].previousSibling;
                    var next = $toInsert.last()[0].nextSibling;

                    if (prev) {
                        $toInsert.detach();
                        self.trigger_up('request_history_undo_record', {$target: $(prev)});
                        $toInsert.insertAfter(prev);
                    } else if (next) {
                        $toInsert.detach();
                        self.trigger_up('request_history_undo_record', {$target: $(next)});
                        $toInsert.insertBefore(next);
                    } else {
                        var $parent = $toInsert.parent();
                        $toInsert.detach();
                        self.trigger_up('request_history_undo_record', {$target: $parent});
                        $parent.prepend($toInsert);
                    }

                    var $target = $toInsert;

                    _.defer(function () {
                        self.trigger_up('snippet_dropped', {$target: $target});
                        self._disableUndroppableSnippets();

                        self._callForEachChildSnippet($target, function (editor, $snippet) {
                            return editor.buildSnippet();
                        }).then(function () {
                            $target.trigger('content_changed');
                            return self._updateInvisibleDOM();
                        });
                    });
                } else {
                    $toInsert.remove();
                }
            },
        });
    },
    /**
     * Adds the 'o_default_snippet_text' class on nodes which contain only
     * non-empty text nodes. Those nodes are then auto-selected by the editor
     * when they are clicked.
     *
     * @private
     * @param {jQuery} [$in] - the element in which to search, default to the
     *                       snippet bodies in the menu
     */
    _registerDefaultTexts: function ($in) {
        if ($in === undefined) {
            $in = this.$snippets.find('.oe_snippet_body');
        }

        $in.find('*').addBack()
            .contents()
            .filter(function () {
                return this.nodeType === 3 && this.textContent.match(/\S/);
            }).parent().addClass('o_default_snippet_text');
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Called when a child editor asks for insertion zones to be enabled.
     *
     * @private
     * @param {OdooEvent} ev
     */
    _onActivateInsertionZones: function (ev) {
        this._activateInsertionZones(ev.data.$selectorSiblings, ev.data.$selectorChildren);
    },
    /**
     * Called when a child editor asks to deactivate the current snippet
     * overlay.
     *
     * @private
     */
    _onActivateSnippet: function (ev) {
        this._activateSnippet(ev.data.$snippet, ev.data.previewMode, ev.data.ifInactiveOptions);
    },
    /**
     * Called when a child editor asks to operate some operation on all child
     * snippet of a DOM element.
     *
     * @private
     * @param {OdooEvent} ev
     */
    _onCallForEachChildSnippet: function (ev) {
        this._callForEachChildSnippet(ev.data.$snippet, ev.data.callback);
    },
    /**
     * Called when the overlay dimensions/positions should be recomputed.
     *
     * @private
     */
    _onOverlaysCoverUpdate: function () {
        this.snippetEditors.forEach(editor => {
            editor.cover();
        });
    },
    /**
     * Called when a child editor asks to clone a snippet, allows to correctly
     * call the _onClone methods if the element's editor has one.
     *
     * @private
     * @param {OdooEvent} ev
     */
    _onCloneSnippet: function (ev) {
        ev.stopPropagation();
        this._createSnippetEditor(ev.data.$snippet).then(editor => {
            editor.clone();
        });
    },
    /**
     * Called when a child editor asks to deactivate the current snippet
     * overlay.
     *
     * @private
     */
    _onDeactivateSnippet: function () {
        this._activateSnippet(false);
    },
    /**
     * Called when a snippet has moved in the page.
     *
     * @private
     * @param {OdooEvent} ev
     */
    _onDragAndDropStop: async function (ev) {
        await this._destroyEditors();
        await this._activateSnippet(ev.data.$snippet);
    },
    /**
     * Called when a snippet editor asked to disable itself and to enable its
     * parent instead.
     *
     * @private
     * @param {OdooEvent} ev
     */
    _onGoToParent: function (ev) {
        ev.stopPropagation();
        this._activateSnippet(ev.data.$snippet.parent());
    },
    /**
     * @private
     */
    _onHideOverlay: function () {
        for (const editor of this.snippetEditors) {
            editor.toggleOverlay(false);
        }
    },
    /**
     * @private
     * @param {Event} ev
     */
    _onInstallBtnClick: function (ev) {
        var self = this;
        var $snippet = $(ev.currentTarget).closest('[data-module-id]');
        var moduleID = $snippet.data('moduleId');
        var name = $snippet.attr('name');
        new Dialog(this, {
            title: _.str.sprintf(_t("Install %s"), name),
            size: 'medium',
            $content: $('<div/>', {text: _.str.sprintf(_t("Do you want to install the %s App?"), name)}).append(
                $('<a/>', {
                    target: '_blank',
                    href: '/web#id=' + moduleID + '&view_type=form&model=ir.module.module&action=base.open_module_tree',
                    text: _t("More info about this app."),
                    class: 'ml4',
                })
            ),
            buttons: [{
                text: _t("Save and Install"),
                classes: 'btn-primary',
                click: function () {
                    this.$footer.find('.btn').toggleClass('o_hidden');
                    this._rpc({
                        model: 'ir.module.module',
                        method: 'button_immediate_install',
                        args: [[moduleID]],
                    }).then(() => {
                        self.trigger_up('request_save', {
                            reload: false,
                            onSuccess: function () {
                                window.location.href = window.location.origin + window.location.pathname + '?enable_editor=1';
                            },
                        });
                    }).guardedCatch(reason => {
                        reason.event.preventDefault();
                        this.close();
                        self.displayNotification({
                            title: _t("Something went wrong."),
                            message: _.str.sprintf(_t("The module <strong>%s</strong> could not be installed."), name),
                            type: 'danger',
                            sticky: true,
                        });
                    });
                },
            }, {
                text: _t("Install in progress"),
                icon: 'fa-spin fa-spinner fa-pulse mr8',
                classes: 'btn-primary disabled o_hidden',
            }, {
                text: _t("Cancel"),
                close: true,
            }],
        }).open();
    },
    /**
     * @private
     * @param {Event} ev
     */
    _onInvisibleEntryClick: async function (ev) {
        ev.preventDefault();
        const $snippet = $(this.invisibleDOMMap.get(ev.currentTarget));
        const isVisible = await this._mutex.exec(async () => {
            const editor = await this._createSnippetEditor($snippet);
            return editor.toggleTargetVisibility();
        });
        $(ev.currentTarget).find('.fa')
            .toggleClass('fa-eye', isVisible)
            .toggleClass('fa-eye-slash', !isVisible);
        return this._activateSnippet(isVisible ? $snippet : false);
    },
    /**
     * @private
     */
    _onBlockPreviewOverlays: function (ev) {
        this._blockPreviewOverlays = true;
    },
    /**
     * @private
     */
    _onUnblockPreviewOverlays: function (ev) {
        this._blockPreviewOverlays = false;
    },
    /**
     * @private
     * @param {OdooEvent} ev
     */
    _onRemoveSnippet: function (ev) {
        ev.stopPropagation();
        this._createSnippetEditor(ev.data.$snippet).then(function (editor) {
            editor.removeSnippet();
        });
    },
    /**
     * @private
     * @param {OdooEvent} ev
     * @param {Object} ev.data
     * @param {function} ev.data.exec
     */
    _onSnippetEditionRequest: function (ev) {
        this._mutex.exec(ev.data.exec);
    },
    /**
     * @private
     */
    _onSnippetCloned: function (ev) {
        this._updateInvisibleDOM();
    },
    /**
     * Called when a snippet is removed -> checks if there is draggable snippets
     * to enable/disable as the DOM changed.
     *
     * @private
     */
    _onSnippetRemoved: function () {
        this._disableUndroppableSnippets();
        this._updateInvisibleDOM();
    },
    /**
     * @private
     * @param {OdooEvent} ev
     */
    _onSnippetOptionVisibilityUpdate: async function (ev) {
        if (!ev.data.show) {
            await this._activateSnippet(false);
        }
        await this._updateInvisibleDOM(); // Re-render to update status
    },
    /**
     * @private
     * @param {OdooEvent} ev
     */
    _onUpdateCustomizeElements: function (ev) {
        this._closeWidgets();
        while (this.customizePanel.firstChild) {
            this.customizePanel.removeChild(this.customizePanel.firstChild);
        }
        ev.data.customize$Elements.forEach($el => {
            this.customizePanel.appendChild($el[0]);
        });
        var customize = !!ev.data.customize$Elements.length;
        this.$('#o_scroll').toggleClass('d-none', customize);
        this.$('.o_we_add_snippet_btn').toggleClass('active', !customize);
        this.customizePanel.classList.toggle('d-none', !customize);
        this.$('.o_we_customize_snippet_btn').toggleClass('active', customize);
    },
    /**
     * Called when an user value widget is being opened -> close all the other
     * user value widgets of all editors.
     */
    _onUserValueWidgetOpening: function () {
        this._closeWidgets();
    },
});

return {
    Class: SnippetsMenu,
    Editor: SnippetEditor,
    globalSelector: globalSelector,
};
});
