odoo.define('web_editor.snippet.editor', function (require) {
'use strict';

var concurrency = require('web.concurrency');
var core = require('web.core');
var Dialog = require('web.Dialog');
var dom = require('web.dom');
var Widget = require('web.Widget');
var config = require('web.config');
var snippetOptions = require('web_editor.snippets.options');
const {ColorPaletteWidget} = require('web_editor.ColorPalette');
const SmoothScrollOnDrag = require('web/static/src/js/core/smooth_scroll_on_drag.js');
const {getCSSVariableValue} = require('web_editor.utils');

var _t = core._t;

var globalSelector = {
    closest: () => $(),
    all: () => $(),
    is: () => false,
};

// jQuery extensions
$.extend($.expr[':'], {
    o_editable: function (node, i, m) {
        while (node) {
            if (node.className && _.isString(node.className)) {
                if (node.className.indexOf('o_not_editable') !== -1) {
                    return false;
                }
                if (node.className.indexOf('o_editable') !== -1) {
                    return true;
                }
            }
            node = node.parentNode;
        }
        return false;
    },
});

/**
 * Management of the overlay and option list for a snippet.
 */
var SnippetEditor = Widget.extend({
    template: 'web_editor.snippet_overlay',
    xmlDependencies: ['/web_editor/static/src/xml/snippets.xml'],
    events: {
        'click .oe_snippet_remove': '_onRemoveClick',
        'wheel': '_onMouseWheel',
    },
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
    init: function (parent, snippetElement, templateOptions, $editable, snippetMenu, options) {
        this._super.apply(this, arguments);
        this.options = options;
        this.$editable = $editable;
        this.$snippetBlock = $(snippetElement);
        this.$editor = this.getParent().$editor;
        this.$snippetBlock.data('snippet-editor', this);
        // The following class is a hack. There is a possibility of the
        // `$snippetBlock` to be destroyed at some point.
        // For example: The method `updateChangesInWysiwyg` of an "editor option" migth
        // erase $snippetBlock that are children on the current "editor option".
        // In that case, the editor of the child will be erased with the method
        // `updateCurrentSnippetEditorOverlay` because it's target will not be
        // present on the DOM.
        // But because an editor has been previously created, it might need to
        // be cleaned with `cleanForSave`.  Therfore we flag the $snippetBlock
        // with "o_snippet_editor_updated" to recreate editor in order to be
        // able to call `cleanForSave`.
        this.$snippetBlock.addClass("o_snippet_editor_updated");
        this.$body = $(document.body);
        this.templateOptions = templateOptions;
        this.isTargetParentEditable = false;
        this.isTargetMovable = false;
        this.JWEditorLib = options.JWEditorLib;
        this.wysiwyg = options.wysiwyg;
        this.editor = options.wysiwyg.editor;
        this.editorHelpers = this.wysiwyg.editorHelpers;

        this.snippetMenu = snippetMenu;

        this.__isStarted = new Promise(resolve => {
            this.__isStartedResolveFunc = resolve;
        });
    },
    /**
     * @override
     */
    start: function () {
        const self = this;
        var defs = [this._super.apply(this, arguments)];

        // Initialize the associated options (see snippets.options.js)
        defs.push(this._initializeOptions());
        var $customize = this._customize$Elements[this._customize$Elements.length - 1];

        this.isTargetParentEditable = this.$snippetBlock.parent().is(':o_editable');
        this.isTargetMovable = this.isTargetParentEditable && this.isTargetMovable;
        this.isTargetRemovable = this.isTargetParentEditable && !this.$snippetBlock.parent().is('[data-oe-type="image"]');

        // Initialize move/clone/remove buttons
        if (this.isTargetMovable) {
            this.dropped = false;
            const smoothScrollOptions = this.options.getScrollOptions({
                jQueryDraggableOptions: {
                    cursorAt: {
                        left: 15,
                        top: 11,
                    },
                    iframeFix: true,
                    handle: '.o_move_handle',
                    helper: () => {
                        return $('<div class="o_overlay_move_handle"><div class="o_move_handle"/></div>');
                    },
                    start: this._dragAndDropStart.bind(this),
                    stop: (...args) => {
                        // Delay our stop handler so that some summernote handlers
                        // which occur on mouseup (and are themself delayed) are
                        // executed first (this prevents the library to crash
                        // because our stop handler may change the DOM).
                        setTimeout(() => {
                            this._onDragAndDropStop(...args);
                        }, 0);
                    },
                },
                dropzones: function () {
                    return self.$editor.find('.oe_drop_zone');
                },
                over: function (ui, droppable) {
                    if (!self.dropped) {
                        $(droppable).addClass('d-none').after(self.$snippetBlock);
                        self.dropped = true;
                    }
                },
                out: function (ui, droppable) {
                    if (self.dropped) {
                        $(droppable).removeClass('d-none');
                        self.$snippetBlock.detach();
                        self.dropped = false;
                    }
                },
            });
            this.draggableComponent = new SmoothScrollOnDrag(this, this.$el, this.$editable.find('#wrapwrap').addBack().last(), smoothScrollOptions);
        } else {
            this.$('.o_overlay_move_options').addClass('d-none');
            $customize.find('.oe_snippet_clone').addClass('d-none');
        }

        if (!this.isTargetRemovable) {
            this.$el.add($customize).find('.oe_snippet_remove').addClass('d-none');
        }

        var _animationsCount = 0;
        var postAnimationCover = _.throttle(() => this.cover(), 100);
        this.$snippetBlock.on('transitionstart.snippet_editor, animationstart.snippet_editor', () => {
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
        this.$snippetBlock.on('transitionend.snippet_editor, animationend.snippet_editor', postAnimationCover);

        return Promise.all(defs).then(() => {
            this.__isStartedResolveFunc(this);
        });
    },
    /**
     * @override
     */
    destroy: function () {
        // Before actually destroying a snippet editor, notify the parent
        // about it so that it can update its list of alived snippet editors.
        this.trigger_up('snippet_editor_destroyed');

        this._super(...arguments);
        this.$snippetBlock.removeData('snippet-editor');
        this.$snippetBlock.off('.snippet_editor');
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
        for (var i in this.snippetOptionInstances) {
            this.snippetOptionInstances[i].onBuilt();
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
        await this.toggleTargetVisibility(!this.$snippetBlock.hasClass('o_snippet_invisible'));
        const proms = _.map(this.snippetOptionInstances, async option => {
            await option.cleanForSave();
        });
        await Promise.all(proms);
    },
    /**
     * Closes all widgets of all options.
     */
    closeWidgets: function () {
        if (!this.snippetOptionInstances || !this.areOptionsShown()) {
            return;
        }
        Object.keys(this.snippetOptionInstances).forEach(key => {
            this.snippetOptionInstances[key].closeWidgets();
        });
    },
    /**
     * Makes the editor overlay cover the associated snippet.
     */
    cover: function () {
        if (!this.isShown() || !this.$snippetBlock.length) {
            return;
        }

        const $modal = this.$snippetBlock.find('.modal');
        const $target = $modal.length ? $modal : this.$snippetBlock;
        const targetEl = $target[0];

        // Check first if the target is still visible, otherwise we have to
        // hide it. When covering all element after scroll for instance it may
        // have been hidden (part of an affixed header for example) or it may
        // be outside of the viewport (the whole header during an effect for
        // example).
        const rect = targetEl.getBoundingClientRect();
        const vpWidth = window.innerWidth || document.documentElement.clientWidth;
        const vpHeight = window.innerHeight || document.documentElement.clientHeight;
        const isInViewport = (
            rect.bottom > -0.1 &&
            rect.right > -0.1 &&
            (vpHeight - rect.top) > -0.1 &&
            (vpWidth - rect.left) > -0.1
        );
        const hasSize = ( // :visible not enough for images
            Math.abs(rect.bottom - rect.top) > 0.01 &&
            Math.abs(rect.right - rect.left) > 0.01
        );
        if (!isInViewport || !hasSize || !this.$snippetBlock.is(`:visible`)) {
            this.toggleOverlayVisibility(false);
            return;
        }

        // Now cover the element
        const offset = $target.offset();
        var manipulatorOffset = this.$el.parent().offset();
        offset.top -= manipulatorOffset.top;
        offset.left -= manipulatorOffset.left;
        this.$el.css({
            width: $target.outerWidth(),
            left: offset.left,
            top: offset.top,
        });
        this.$('.o_handles').css('height', $target.outerHeight());

        const editableOffsetTop = this.$editable.offset().top - manipulatorOffset.top;
        this.$el.toggleClass('o_top_cover', offset.top - editableOffsetTop < 25);
    },
    /**
     * DOMElements have a default name which appears in the overlay when they
     * are being edited. This method retrieves this name; it can be defined
     * directly in the DOM thanks to the `data-name` attribute.
     */
    getName: function () {
        if (this.$snippetBlock.data('name') !== undefined) {
            return this.$snippetBlock.data('name');
        }
        if (this.$snippetBlock.is('img')) {
            return _t("Image");
        }
        if (this.$snippetBlock.parent('.row').length) {
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
    isSticky: function () {
        return this.$el && this.$el.hasClass('o_we_overlay_sticky');
    },
    /**
     * @returns {boolean}
     */
    isTargetVisible: function () {
        return (this.$snippetBlock[0].dataset.invisible !== '1');
    },
    /**
     * Removes the associated snippet from the DOM and destroys the associated
     * editor (itself).
     *
     * @returns {Promise}
     */
    removeSnippet: async function () {
        this.toggleOverlay(false);
        this.toggleOptions(false);

        const removeSnippet = async (context) => {
            await new Promise(resolve => {
                this.trigger_up('call_for_each_child_snippet', {
                    $snippet: this.$snippetBlock,
                    callback: async function (editor, $snippet) {
                        for (const i in editor.snippetOptionInstances) {
                            await editor.snippetOptionInstances[i].onRemove(context);
                        }
                    },
                    resolve: resolve,
                });
            });

            this.trigger_up('go_to_parent', {$snippet: this.$snippetBlock});
            var $parent = this.$snippetBlock.parent();
            this.$snippetBlock.find('*').addBack().tooltip('dispose');
            // The snippet has to be removed directly in jquery as well for the
            // synchronous bubbling up system to remove the empty parent.
            // Ideally, we should simply call remove inside a mutations observer
            // callback such that the removal is synchronous while the vdom is
            // updated through observed mutations without calling remove twice.
            this.$snippetBlock.remove();
            await this.editorHelpers.remove(context, this.$snippetBlock[0]);
            this.$el.remove();

            var node = $parent[0];
            if (node && node.firstChild) {
                if (!node.firstChild.tagName && node.firstChild.textContent === ' ') {
                    await this.editorHelpers.remove(context, node.firstChild);
                }
            }

            if ($parent.closest(':data("snippet-editor")').length) {
                var editor = $parent.data('snippet-editor');
                while (!editor) {
                    var $nextParent = $parent.parent();
                    if (isEmptyAndRemovable($parent)) {
                        await this.editorHelpers.remove(context, this.$parent[0]);
                    }
                    $parent = $nextParent;
                    editor = $parent.data('snippet-editor');
                }
                if (isEmptyAndRemovable($parent, editor)) {
                    // TODO maybe this should be part of the actual Promise being
                    // returned by the function ?
                    await new Promise((resolve)=> {
                        setTimeout(() => editor.removeSnippet().then(resolve));
                    });
                }
            }

            await new Promise((resolve) => this.trigger_up('snippet_removed', {onFinish: resolve, context: context}));
            this.destroy();
            const childs = this.snippetMenu.getChildrenSnippetBlock(this.$snippetBlock);
            for (const child of childs) {
                const snippetEditor = $(child).data('snippet-editor');
                if (snippetEditor) {
                    snippetEditor.destroy();
                }
            }
            $parent.trigger('content_changed');

            function isEmptyAndRemovable($el, editor) {
                editor = editor || $el.data('snippet-editor');
                return $el.children().length === 0 && $el.text().trim() === ''
                    && !$el.hasClass('oe_structure') && (!editor || editor.isTargetParentEditable);
            }
        };
        await this.wysiwyg.editor.execCommand(removeSnippet);
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

        // Show/hide overlay in preview mode or not
        this.$el.toggleClass('oe_active', show);
        this.cover();
        this.toggleOverlayVisibility(show);
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
        const proms = [];
        this._customize$Elements.forEach(($el, i) => {
            const editor = $el.data('editor');
            const options = _.chain(editor.snippetOptionInstances).values().sortBy('__order')
                            .value();
            // TODO ideally: should account the async parts of updateUI and
            // allow async parts in onFocus/onBlur.
            if (show) {
                // All onFocus before all updateUI as the onFocus of an option
                // might affect another option (like updating the $target)
                options.forEach(option => proms.push(option.onFocus()));
                options.forEach(option => proms.push(option.updateUI()));
            } else {
                options.forEach(option => proms.push(option.onBlur()));
            }
        });
        return Promise.all(proms);
    },
    /**
     * @param {boolean} [show]
     * @returns {Promise<boolean>}
     */
    toggleTargetVisibility: async function (show) {
        show = this._toggleVisibilityStatus(show);
        var options = _.values(this.snippetOptionInstances);
        const proms = _.sortBy(options, '__order').map(option => {
            return show ? option.onTargetShow() : option.onTargetHide();
        });
        await Promise.all(proms);
        return show;
    },
    /**
     * @param {boolean} [show=false]
     */
    toggleOverlayVisibility: function (show) {
        if (this.$el && !this.scrollingTimeout) {
            this.$el.toggleClass('o_overlay_hidden', !show && this.isShown());
        }
    },
    /**
     * Clones the current snippet.
     *
     * @private
     * @param {boolean} recordUndo
     */
    clone: async function (recordUndo) {
        this.trigger_up('snippet_will_be_cloned', {$target: this.$snippetBlock});

        const $clonedContent = this.$snippetBlock.clone(false);

        const vNodes = await this.editorHelpers.insertHtml(this.wysiwyg.editor, $clonedContent[0].outerHTML, this.$snippetBlock[0], 'AFTER');
        const $clone = $(this.editorHelpers.getDomNodes(vNodes)[0]);

        await new Promise(resolve => {
            this.trigger_up('call_for_each_child_snippet', {
                $snippet: $clone,
                callback: function (editor, $snippet) {
                    for (const i in editor.snippetOptionInstances) {
                        editor.snippetOptionInstances[i].onClone({
                            isCurrent: ($snippet.is($clone)),
                        });
                    }
                    resolve();
                },
            });
        });
        this.trigger_up('snippet_cloned', {$target: $clone, $origin: this.$snippetBlock});

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
        this.snippetOptionInstances = {};
        this.selectorSiblings = [];
        this.selectorChildren = [];

        var $element = this.$snippetBlock.parent();
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
        const $optionsSectionBtnGroup = $optionsSection.find('we-top-button-group');
        $optionsSectionBtnGroup.contents().each((i, node) => {
            if (node.nodeType === Node.TEXT_NODE) {
                node.parentNode.removeChild(node);
            }
        });
        $optionsSection.on('mouseenter', this._onOptionsSectionMouseEnter.bind(this));
        $optionsSection.on('mouseleave', this._onOptionsSectionMouseLeave.bind(this));
        $optionsSection.on('click', 'we-title > span', this._onOptionsSectionClick.bind(this));
        $optionsSection.on('click', '.oe_snippet_clone', this._onCloneClick.bind(this));
        $optionsSection.on('click', '.oe_snippet_remove', this._onRemoveClick.bind(this));
        this._customize$Elements.push($optionsSection);

        // TODO get rid of this when possible (made as a fix to support old
        // theme options)
        this.$el.data('$optionsSection', $optionsSection);

        var orderIndex = 0;
        var defs = _.map(this.templateOptions, option => {
            if (!option.selector.is(this.$snippetBlock)) {
                return;
            }
            if (option['drop-near']) {
                this.selectorSiblings.push(option['drop-near']);
            }
            if (option['drop-in']) {
                this.selectorChildren.push(option['drop-in']);
            }

            var optionName = option.id;
            const optionInstance = new (snippetOptions.registry[optionName] || snippetOptions.SnippetOptionWidget)(
                this,
                option.$el.children(),
                () => option.base_target ? this.$snippetBlock.find(option.base_target).eq(0) : this.$snippetBlock,
                this.$el,
                _.extend({
                    optionName: optionName,
                    snippetName: this.getName(),
                }, option.data),
                this.options
            );
            var optionId = optionName || _.uniqueId('option');
            if (this.snippetOptionInstances[optionId]) {
                // If two snippet options use the same option name (and so use
                // the same JS option), store the subsequent ones with a unique
                // ID (TODO improve)
                optionId = _.uniqueId(optionId);
            }
            this.snippetOptionInstances[optionId] = optionInstance;
            optionInstance.__order = orderIndex++;

            if (option.forceNoDeleteButton) {
                this.$el.add($optionsSection).find('.oe_snippet_remove').addClass('d-none');
            }
            return optionInstance.appendTo(document.createDocumentFragment());
        });

        this.isTargetMovable = (this.selectorSiblings.length > 0 || this.selectorChildren.length > 0);

        this.$el.find('[data-toggle="dropdown"]').dropdown();

        return Promise.all(defs).then(() => {
            const options = _.sortBy(this.snippetOptionInstances, '__order');
            const firstOptions = []
            options.forEach(option => {
                if (option.isTopOption) {
                    if (option.isTopFirstOption) {
                        firstOptions.push(option);
                    } else {
                        $optionsSectionBtnGroup.prepend(option.$el);
                    }
                } else {
                    $optionsSection.append(option.$el);
                }
            });
            firstOptions.forEach(option => {
                $optionsSectionBtnGroup.prepend(option.$el);
            });
            $optionsSection.toggleClass('d-none', options.length === 0);
        });
    },
    /**
     * Reset the options target in case the reference is outdated.
     *
     * This can happen with the method `updateChangesInWysiwyg` on a `SnippetOption`.
     *
     * @private
     */
    _resetOptionsTarget() {
        if (!this.snippetOptionInstances) return;
        for (const snippetOption of Object.values(this.snippetOptionInstances)) {
            snippetOption.resetOptionTarget();
        }
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
            delete this.$snippetBlock[0].dataset.invisible;
        } else {
            this.$snippetBlock[0].dataset.invisible = '1';
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
    _dragAndDropStart: function () {
        var self = this;
        this.dropped = false;
        self.size = {
            width: self.$snippetBlock.width(),
            height: self.$snippetBlock.height()
        };
        self.$snippetBlock.after('<div class="oe_drop_clone" style="display: none;"/>');
        self.$snippetBlock.detach();
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

        this.trigger_up('go_to_parent', {$snippet: this.$snippetBlock});
        this.trigger_up('activate_insertion_zones', {
            $selectorSiblings: $selectorSiblings,
            $selectorChildren: $selectorChildren,
        });

        this.$body.addClass('move-important');

        this.trigger_up('drag_and_drop_start', {
            $snippet: this.$snippetBlock,
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
    _onDragAndDropStop: async function (ev, ui) {
        // TODO lot of this is duplicated code of the d&d feature of snippets
        if (!this.dropped) {
            var $el = $.nearest({x: ui.position.left, y: ui.position.top}, '.oe_drop_zone', {container: document.body}).first();
            if ($el.length) {
                $el.after(this.$snippetBlock);
                this.dropped = true;
            }
        }

        this.$editable.find('.oe_drop_zone').remove();

        var prev = this.$snippetBlock.first()[0].previousSibling;
        var next = this.$snippetBlock.last()[0].nextSibling;
        var $parent = this.$snippetBlock.parent();

        var $clone = this.$editable.find('.oe_drop_clone');
        if (prev === $clone[0]) {
            prev = $clone[0].previousSibling;
            this.dropped = false;
        } else if (next === $clone[0]) {
            next = $clone[0].nextSibling;
            this.dropped = false;
        }
        $clone.after(this.$snippetBlock);
        var $from = $clone.parent();

        this.$el.removeClass('d-none');
        this.$body.removeClass('move-important');
        $clone.remove();

        dom.scrollTo(this.$snippetBlock[0], {extraOffset: 50});

        if (this.dropped) {
            if (prev) {
                this.$snippetBlock.insertAfter(prev);
            } else if (next) {
                this.$snippetBlock.insertBefore(next);
            } else {
                $parent.prepend(this.$snippetBlock);
            }

            const jwEditor = this.wysiwyg.editor;
            const moveSnippet = async (context) => {
                const node = this.editorHelpers.getNodes(this.$snippetBlock[0])[0];
                const prevNodes = this.editorHelpers.getNodes(prev);
                if (prevNodes.length) {
                    prevNodes.pop().after(node);
                    return;
                }
                const nextNodes = this.editorHelpers.getNodes(next);
                if (nextNodes.length) {
                    nextNodes[0].before(node);
                    return;
                }
                const parentNodes = this.editorHelpers.getNodes($parent[0]);
                if (parentNodes.length) {
                    parentNodes.pop().append(node);
                    return;
                }
            };
            await jwEditor.execCommand(moveSnippet);

            for (var i in this.snippetOptionInstances) {
                await this.snippetOptionInstances[i].onMove();
            }
        }

        this.trigger_up('drag_and_drop_stop', {
            $snippet: this.$snippetBlock,
        });

        if (this.dropped) {
            this.$snippetBlock.trigger('content_changed');
            $from.trigger('content_changed');
        }
    },
    /**
     * @private
     */
    _onOptionsSectionMouseEnter: function (ev) {
        if (!this.$snippetBlock.is(':visible')) {
            return;
        }
        this.trigger_up('activate_snippet', {
            $element: this.$snippetBlock,
            previewMode: true,
        });
    },
    /**
     * @private
     */
    _onOptionsSectionMouseLeave: function (ev) {
        this.trigger_up('deactivate_snippet', {
            previewMode: true,
        });
    },
    /**
     * @private
     */
    _onOptionsSectionClick: function (ev) {
        this.trigger_up('activate_snippet', {
            $element: this.$snippetBlock,
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
    _onOptionUpdate: async function (ev) {
        var self = this;
        // If multiple option names are given, we suppose it should not be
        // propagated to parent editor
        if (ev.data.optionNames) {
            ev.stopPropagation();
            for (const name of ev.data.optionNames) {
                await notifyForEachMatchedOption(name);
            }
        }
        // If one option name is given, we suppose it should be handle by the
        // first parent editor which can do it
        if (ev.data.optionName) {
            await notifyForEachMatchedOption(ev.data.optionName, ev);
        }

        async function notifyForEachMatchedOption(name, eventToStop) {
            const regex = new RegExp('^' + name + '\\d+$');
            for (const key in self.snippetOptionInstances) {
                if (key === name || regex.test(key)) {
                    if (eventToStop) {
                        eventToStop.stopPropagation();
                    }
                    await self.snippetOptionInstances[key].notify(ev.data.name, ev.data.data);
                }
            }
        }
        ev.data.resolve && ev.data.resolve();
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
        this.removeSnippet();
    },
    /**
     * @private
     * @param {OdooEvent} ev
     */
    _onSnippetOptionUpdate: async function (ev) {
        const proms1 = Object.keys(this.snippetOptionInstances).map(key => {
            return this.snippetOptionInstances[key].updateUI({
                noVisibility: true,
            });
        });
        await Promise.all(proms1);

        const proms2 = Object.keys(this.snippetOptionInstances).map(key => {
            return this.snippetOptionInstances[key].updateUIVisibility();
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
        ev.stopPropagation();
        for (const key of Object.keys(this.snippetOptionInstances)) {
            const widget = this.snippetOptionInstances[key].findWidget(ev.data.name);
            if (widget) {
                ev.data.onSuccess(widget);
                return;
            }
        }
    },
    /**
     * Called when the 'mouse wheel' is used when hovering over the overlay.
     * Disable the pointer events to prevent page scrolling from stopping.
     *
     * @private
     * @param {Event} ev
     */
    _onMouseWheel: function (ev) {
        ev.stopPropagation();
        this.$el.css('pointer-events', 'none');
        clearTimeout(this.wheelTimeout);
        this.wheelTimeout = setTimeout(() => {
            this.$el.css('pointer-events', '');
        }, 250);
    },
});

/**
* Management of drag&drop menu and snippet related behaviors in the page.
*/
var SnippetsMenu = Widget.extend({
    id: 'oe_snippets',
    cacheSnippetTemplate: {},
    events: {
        'click .oe_snippet': '_onSnippetClick',
        'click .o_install_btn': '_onInstallBtnClick',
        'click .o_we_add_snippet_btn': '_onBlocksTabClick',
        'click .o_we_invisible_entry': '_onInvisibleEntryClick',
        'click #snippet_custom .o_delete_btn': '_onDeleteBtnClick',
        'mousedown': '_onMouseDown',
        'input .o_snippet_search_filter_input': '_onSnippetSearchInput',
        'click .o_snippet_search_filter_reset': '_onSnippetSearchResetClick',
        'click .o_we_website_top_actions button[data-action=save]': '_onSaveClick',
        'click .o_we_website_top_actions button[data-action=cancel]': '_onDiscardClick',
        'click .o_we_website_top_actions button[data-action=mobile]': '_onMobilePreviewClick',
    },
    custom_events: {
        'activate_insertion_zones': '_onActivateInsertionZones',
        'activate_snippet': '_onActivateSnippet',
        'call_for_each_child_snippet': '_onCallForEachChildSnippet',
        'clone_snippet': '_onCloneSnippet',
        'cover_update': '_onOverlaysCoverUpdate',
        'deactivate_snippet': '_onDeactivateSnippet',
        'drag_and_drop_start': '_onDragAndDropStart',
        'drag_and_drop_stop': '_onDragAndDropStop',
        'get_snippet_versions': '_onGetSnippetVersions',
        'go_to_parent': '_onGoToParent',
        'remove_snippet': '_onRemoveSnippet',
        'snippet_edition_request': '_onSnippetEditionRequest',
        'snippet_editor_destroyed': '_onSnippetEditorDestroyed',
        'snippet_removed': '_onSnippetRemoved',
        'snippet_cloned': '_onSnippetCloned',
        'snippet_option_visibility_update': '_onSnippetOptionVisibilityUpdate',
        'snippet_thumbnail_url_request': '_onSnippetThumbnailURLRequest',
        'reload_snippet_dropzones': '_disableUndroppableSnippets',
        'request_save': '_onSaveRequest',
        'update_customize_elements': '_onUpdateCustomizeElements',
        'hide_overlay': '_onHideOverlay',
        'block_preview_overlays': '_onBlockPreviewOverlays',
        'unblock_preview_overlays': '_onUnblockPreviewOverlays',
        'user_value_widget_opening': '_onUserValueWidgetOpening',
        'user_value_widget_closing': '_onUserValueWidgetClosing',
        'reload_snippet_template': '_onReloadSnippetTemplate',
    },
    // enum of the SnippetsMenu's tabs.
    tabs: {
        BLOCKS: 'blocks',
        OPTIONS: 'options',
        THEME: 'theme',
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
        this._enabledSnippetEditorsHierarchy = [];

        this._mutex = new concurrency.Mutex();

        this.selectorEditableArea = options.selectorEditableArea;
        this.$editor = options.$el;
        this.$body = $(document.body);

        this.wysiwyg = options.wysiwyg;

        this.JWEditorLib = options.JWEditorLib;
        if (this.JWEditorLib) {
            const jwEditor = this.wysiwyg.editor;
            const layout = jwEditor.plugins.get(this.JWEditorLib.Layout);
            this.layoutEngine = layout.engines.dom;
            this.nodeToEditor = new Map();
            this.editorHelpers = this.wysiwyg.editorHelpers;
        }

        this._notActivableElementsSelector = [
            '#web_editor-top-edit',
            '.o_we_website_top_actions',
            '#oe_snippets',
            '#oe_manipulators',
            '.o_technical_modal',
            '.oe_drop_zone',
            '.o_notification_manager',
            '.o_we_no_overlay',
            '.ui-autocomplete',
            '.modal .close',
            '.o_we_crop_widget',
        ].join(', ');

        this.loadingTimers = {};
        this.loadingElements = {};
        this.$snippetEditorArea = options.$snippetEditorArea;
    },
    /**
     * @override
     */
    willStart: function () {
        // Preload colorpalette dependencies without waiting for them. The
        // widget have huge chances of being used by the user (clicking on any
        // text will load it). The colorpalette itself will do the actual
        // waiting of the loading completion.
        ColorPaletteWidget.loadDependencies(this);
        return this._super(...arguments);
    },
    /**
     * @override
     */
    async start() {
        var defs = [this._super.apply(this, arguments)];
        this.ownerDocument = this.$el[0].ownerDocument;
        this.$document = $(this.ownerDocument);
        this.window = this.ownerDocument.defaultView;
        this.$window = $(this.window);

        this.customizePanel = document.createElement('div');
        this.customizePanel.classList.add('o_we_customize_panel', 'd-none');

        this.textEditorPanelEl = document.createElement('div');
        this.textEditorPanelEl.classList.add('o_we_snippet_text_tools', 'd-none');

        if (this.options.onlyStyleTab) {
            await this._loadSnippetsTemplates();
            this.$el.find('.o_we_website_top_actions').removeClass('d-none');
            this.$('.o_snippet_search_filter').addClass('d-none');
            this.$('#o_scroll').addClass('d-none');
            this.$('#snippets_menu button').removeClass('active').prop('disabled', true);
            this.$('.o_we_customize_snippet_btn').addClass('active').prop('disabled', false);
            this.$('o_we_ui_loading').addClass('d-none');
            $(this.customizePanel).removeClass('d-none');
            this._addJabberwockToolbar();
            return Promise.all(defs);
        }

        this.invisibleDOMPanelEl = document.createElement('div');
        this.invisibleDOMPanelEl.classList.add('o_we_invisible_el_panel');
        this.invisibleDOMPanelEl.appendChild(
            $('<div/>', {
                text: _t('Invisible Elements'),
                class: 'o_panel_header',
            })[0]
        );

        this.options.getScrollOptions = this._getScrollOptions.bind(this);

        // Fetch snippet templates and compute it
        defs.push((async () => {
            await this._loadSnippetsTemplates();
            // enable the toolbar actions for the jabberwock editor
            this.$el.find('.o_we_website_top_actions').removeClass('d-none');
            await this._updateInvisibleDOM();
        })());

        core.bus.on('deactivate_snippet', this, this._onDeactivateSnippet);

        this.$window.on('mousedown.snippets_menu', this._onContentMouseDown.bind(this));
        this.$window.on('mousedown-iframe.snippets_menu', this._onContentMouseDown.bind(this));

        // Adapt overlay covering when the window is resized / content changes
        var throttledCoverUpdate = _.throttle(() => {
            this.updateCurrentSnippetEditorOverlay();
        }, 50);
        this.$window.on('resize.snippets_menu', throttledCoverUpdate);
        this.$window.on('content_changed.snippets_menu', throttledCoverUpdate);

        // On keydown add a class on the active overlay to hide it and show it
        // again when the mouse moves
        this.$document.on('keydown.snippets_menu', () => {
            this.__overlayKeyWasDown = true;
            this.snippetEditors.forEach(editor => {
                editor.toggleOverlayVisibility(false);
            });
        });
        this.$document.on('mousemove.snippets_menu, mousedown.snippets_menu', _.throttle(() => {
            if (!this.__overlayKeyWasDown) {
                return;
            }
            this.__overlayKeyWasDown = false;
            this.snippetEditors.forEach(editor => {
                editor.toggleOverlayVisibility(true);
                editor.cover();
            });
            this.updateCurrentSnippetEditorOverlay();
        }, 250));
        this.$editor.find('#wrapwrap').on('scroll.snippets_menu', () => {
            this.updateCurrentSnippetEditorOverlay();
        });
        // Hide the active overlay when scrolling.
        // Show it again and recompute all the overlays after the scroll.
        this.$scrollingElement = $().getScrollingElement();
        this.$scrollingElement.on('scroll.snippets_menu', _.throttle(() => {
            for (const editor of this.snippetEditors) {
                editor.toggleOverlayVisibility(false);
            }
            clearTimeout(this.scrollingTimeout);
            this.scrollingTimeout = setTimeout(() => {
                this._scrollingTimeout = null;
                for (const editor of this.snippetEditors) {
                    editor.toggleOverlayVisibility(true);
                    editor.cover();
                }
            }, 250);
        }, 50));

        // Auto-selects text elements with a specific class and remove this
        // on text changes
        this.$document.on('click.snippets_menu', '.o_default_snippet_text', (ev) => {
            ev.preventDefault();
            ev.stopPropagation();
            ev.stopImmediatePropagation();
            const autoSelectDefaultText = async (context) => {
                const $target = $(ev.target);
                const $defaultSnippetText = $target.closest('.o_default_snippet_text');
                await this.editorHelpers.removeClass(context, $defaultSnippetText[0], 'o_default_snippet_text');
                const nodes = this.editorHelpers.getNodes($target[0]);
                this.wysiwyg.editor.selection.select(nodes[0], nodes[nodes.length - 1]);
            };
            this.wysiwyg.editor.execCommand(autoSelectDefaultText);
        });

        const $autoFocusEls = $('.o_we_snippet_autofocus');
        if ($autoFocusEls.length) {
            this._activateSnippet($autoFocusEls.first());
        }
        this._textToolsSwitchingEnabled = true;

        // Add tooltips on we-title elements whose text overflows
        this.$el.tooltip({
            selector: 'we-title',
            placement: 'bottom',
            delay: 100,
            title: function () {
                const el = this;
                // On Firefox, el.scrollWidth is equal to el.clientWidth when
                // overflow: hidden, so we need to update the style before to
                // get the right values.
                el.style.setProperty('overflow', 'scroll', 'important');
                const tipContent = el.scrollWidth > el.clientWidth ? el.innerHTML : '';
                el.style.removeProperty('overflow');
                return tipContent;
            },
        });

        return Promise.all(defs).then(() => {
            this.$('[data-title]').tooltip({
                delay: 100,
                title: function () {
                    return this.classList.contains('active') ? false : this.dataset.title;
                },
            });
        });
    },
    /**
     * @override
     */
    destroy: function () {
        this._super.apply(this, arguments);
        if (this.$window) {
            this.$window.off('.snippets_menu');
            this.$document.off('.snippets_menu');
            this.$scrollingElement.off('.snippets_menu');
            this.$editor.find('#wrapwrap').off('.snippets_menu');
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
        await this._enableLastEditor();
        await this._removeLastSnippetActivated();
        this.trigger_up('ready_to_clean_for_save');
        await this._destroyEditors();
    },
    /**
     * Load snippets.
     * @param {boolean} invalidateCache
     */
    loadSnippets: function (invalidateCache) {
        if (!invalidateCache && this.cacheSnippetTemplate[this.options.snippets]) {
            this._defLoadSnippets = this.cacheSnippetTemplate[this.options.snippets];
            return this._defLoadSnippets;
        }
        this._defLoadSnippets = this._rpc({
            model: 'ir.ui.view',
            method: 'render_public_asset',
            args: [this.options.snippets, {}],
            kwargs: {
                context: this.options.context,
            },
        });
        this.cacheSnippetTemplate[this.options.snippets] = this._defLoadSnippets;
        return this._defLoadSnippets;
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
        for (const snippetEditor of this.snippetEditors) {
            if (snippetEditor.$snippetBlock.closest('body, .note-editable').length) {
                snippetEditor.cover();
                continue;
            }
            // Destroy options whose $target are not in the DOM anymore but
            // only do it once all options executions are done.
            this._mutex.exec(() => snippetEditor.destroy());
        }
    },
    /**
     * @param {JQuery} $snippetBlock
     * @returns {JQuery}
     */
    getChildrenSnippetBlock($snippetBlock) {
        return $snippetBlock.add(globalSelector.all($snippetBlock));
    },
    /**
     * Activate the last snippet that has been activated
     */
    activateLastSnippetBlock() {
        const $lastSnippet = this.$editor.find('.o_we_last_snippet_activated');
        if ($lastSnippet) {
            this._activateSnippet($lastSnippet, $lastSnippet.hasClass('o_we_last_snippet_preview'));
        }
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
                    if (!isFullWidth($zone) && !$zone.hasClass('oe_structure')) {
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
                    if (!isFullWidth($zone) && !$zone.hasClass('oe_structure')) {
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
            $zones = this.$editor.find('.oe_drop_zone > .oe_drop_zone').remove(); // no recursive zones
            count += $zones.length;
            $zones.remove();
        } while (count > 0);

        // Cleaning consecutive zone and up zones placed between floating or
        // inline elements. We do not like these kind of zones.
        $zones = this.$editor.find('.oe_drop_zone:not(.oe_vertical)');
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
        return this._execWithLoadingEffect(() => {
            this.invisibleDOMMap = new Map();
            const $invisibleDOMPanelEl = $(this.invisibleDOMPanelEl);
            $invisibleDOMPanelEl.find('.o_we_invisible_entry').remove();
            const $invisibleSnippets = this.$editor.find('.o_snippet_invisible').addBack('.o_snippet_invisible');

            $invisibleDOMPanelEl.toggleClass('d-none', !$invisibleSnippets.length);

            const proms = _.map($invisibleSnippets, async el => {
                const editor = await this._getSnippetEditor($(el));
                const $invisEntry = $('<div/>', {
                    class: 'o_we_invisible_entry d-flex align-items-center justify-content-between',
                    text: editor.getName(),
                }).append($('<i/>', {class: `fa ${editor.isTargetVisible() ? 'fa-eye' : 'fa-eye-slash'} ml-2`}));
                $invisibleDOMPanelEl.append($invisEntry);
                this.invisibleDOMMap.set($invisEntry[0], el);
            });
            return Promise.all(proms);
        }, false);
    },
    /**
     * Disable the overlay editor of the active snippet and activate the new one.
     * Note 1: if the snippet editor associated to the given snippet is not
     *         created yet, this method will create it.
     * Note 2: if the given DOM element is not a snippet (no editor option), the
     *         first parent which is one is used instead.
     *
     * @private
     * @param {jQuery} $snippetBlock
     *        The DOM element whose editor (and its parent ones) need to be
     *        enabled. Only disable the current one if false is given.
     * @param {boolean} [previewMode=false]
     * @param {boolean} [ifInactiveOptions=false]
     * @returns {Promise<SnippetEditor>}
     *          (might be async when an editor must be created)
     */
    _activateSnippet: async function ($snippetBlock, previewMode, ifInactiveOptions) {
        if (this._blockPreviewOverlays && previewMode) {
            return;
        }
        if (!$snippetBlock.is(':visible')) {
            return;
        }

        const exec = previewMode
            ? action => this._mutex.exec(action)
            : action => this._execWithLoadingEffect(action, false);

        return exec(async () => {
            let snippetEditor;
            // Take the first parent of the provided DOM (or itself) which
            // should have an associated snippet editor and create + enable it.
            if ($snippetBlock.length) {
                const $snippet = globalSelector.closest($snippetBlock);
                if ($snippet.length) {
                    snippetEditor = await this._getSnippetEditor($snippet);
                }
            }
            if (ifInactiveOptions && this._enabledSnippetEditorsHierarchy.includes(snippetEditor)) {
                return snippetEditor;
            }

            const snippetEditorHierarchy = [];
            let currentSnippetEditor = snippetEditor;
            while (currentSnippetEditor && currentSnippetEditor.$snippetBlock) {
                snippetEditorHierarchy.push(currentSnippetEditor);
                currentSnippetEditor = currentSnippetEditor.getParent();
            }


            // First disable all snippet editors...
            for (const currentSnippetEditor of this.snippetEditors) {
                currentSnippetEditor.toggleOverlay(false, previewMode);
                if (!previewMode && !snippetEditorHierarchy.includes(currentSnippetEditor)) {
                    await currentSnippetEditor.toggleOptions(false);
                }
            }

            // ... if no editors are to be enabled, look if any have been
            // enabled previously by a click
            if (!snippetEditor) {
                snippetEditor = this.snippetEditors.find(editor => editor.isSticky());
                previewMode = false;
            }

            // ... then enable the right snippet editor
            if (snippetEditor) {
                snippetEditor.toggleOverlay(true, previewMode);
                await snippetEditor.toggleOptions(true);
            }

            this._enabledSnippetEditorsHierarchy = snippetEditorHierarchy;
            return snippetEditor;
        });
    },
    /**
     * Disable all snippet editors, then enable the last snippet editor.
     *
     * @private
     * @param {boolean} [previewMode=false]
     */
    _enableLastEditor: function(previewMode) {
        this._mutex.exec(async () => {
            // First disable all snippet editors...
            for (const currentSnippetEditor of this.snippetEditors) {
                currentSnippetEditor.toggleOverlay(false, previewMode);
                if (!previewMode) {
                    await currentSnippetEditor.toggleOptions(false);
                }
            }

            // ... then enable the last snippet editor
            const editorToEnable = this.snippetEditors.find(editor => editor.isSticky());
            if (editorToEnable) {
                editorToEnable.toggleOverlay(true, false);
                await editorToEnable.toggleOptions(true);
            }
        });
    },
    /**
     * @private
     * @param {boolean} invalidateCache
     */
    _loadSnippetsTemplates: async function (invalidateCache) {
        return this._execWithLoadingEffect(async () => {
            await this._destroyEditors();
            const html = await this.loadSnippets(invalidateCache);
            await this._computeSnippetTemplates(html);
        }, false);
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
    _callForEachChildSnippet: function ($snippetBlock, callback) {
        const defs = _.map(this.getChildrenSnippetBlock($snippetBlock), async (child) => {
            const $childSnippet = $(child);
            const snippetEditor = await this._getSnippetEditor($childSnippet);
            if (snippetEditor) {
                return await callback.call(this, snippetEditor, $childSnippet);
            }
        });
        return Promise.all(defs);
    },
    /**
     * Close widget for all editors.
     *
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
     * @param {string} selector
     *        jQuery selector that DOM elements must match to be considered as
     *        potential snippet.
     * @param {string} exclude
     *        jQuery selector that DOM elements must *not* match to be
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
    _computeSelectorFunctions: function (selector, exclude, target, noCheck, isChildren) {
        var self = this;

        exclude += `${exclude && ', '}.o_snippet_not_selectable`;

        let filterFunc = function () {
            return !$(this).is(exclude);
        };
        if (target) {
            const oldFilter = filterFunc;
            filterFunc = function () {
                return oldFilter.apply(this) && $(this).find(target).length !== 0;
            };
        }

        // Prepare the functions
        var functions = {
            is: function ($from) {
                return $from.is(selector) && $from.filter(filterFunc).length !== 0;
            },
        };
        if (noCheck) {
            functions.closest = function ($from, parentNode) {
                return $from.closest(selector, parentNode).filter(filterFunc);
            };
            functions.all = function ($from) {
                return ($from ? dom.cssFind($from, selector) : $(selector)).filter(filterFunc);
            };
        } else {
            functions.closest = function ($from, parentNode) {
                var snippetEditors = self.getEditableArea().get();
                return $from.closest(selector, parentNode).filter(function () {
                    var node = this;
                    while (node.parentNode) {
                        if (snippetEditors.indexOf(node) !== -1) {
                            return true;
                        }
                        node = node.parentNode;
                    }
                    return false;
                }).filter(filterFunc);
            };
            functions.all = isChildren ? function ($from) {
                return dom.cssFind($from || self.$editor, selector).filter(filterFunc);
            } : function ($from) {
                $from = $from || self.$editor;
                return $from.filter(selector).add(dom.cssFind($from, selector)).filter(filterFunc);
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
    _computeSnippetTemplates: async function (html) {
        var self = this;
        var $html = $(html);
        var $scroll = $html.siblings('#o_scroll');

        this.templateOptions = [];
        var selectors = [];
        var $dataSelectors = $html.find('[data-selector]');
        $dataSelectors.each(function () {
            var $dataSelector = $(this);
            var selector = $dataSelector.data('selector');
            var exclude = $dataSelector.data('exclude') || '';
            var target = $dataSelector.data('target');
            var noCheck = $dataSelector.data('no-check');
            var optionID = $dataSelector.data('js') || $dataSelector.data('option-name');  // used in tour js as selector
            var option = {
                'id': optionID,
                'base_selector': selector,
                'base_exclude': exclude,
                'base_target': target,
                'selector': self._computeSelectorFunctions(selector, exclude, target, noCheck),
                '$el': $dataSelector,
                'drop-near': $dataSelector.data('drop-near') && self._computeSelectorFunctions($dataSelector.data('drop-near'), '', false, noCheck, true),
                'drop-in': $dataSelector.data('drop-in') && self._computeSelectorFunctions($dataSelector.data('drop-in'), '', false, noCheck),
                'data': _.extend({string: $dataSelector.attr('string')}, $dataSelector.data()),
            };
            self.templateOptions.push(option);
            selectors.push(option.selector);
        });
        $dataSelectors.addClass('d-none');

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
            .each((i, el) => {
                const $snippet = $(el);
                const name = el.getAttribute('name');
                const $snippetBody = $snippet.children().addClass('oe_snippet_body');
                const isCustomSnippet = !!el.closest('#snippet_custom');

                // Associate in-page snippets to their name
                // TODO I am not sure this is useful anymore and it should at
                // least be made more robust using data-snippet
                let snippetClasses = $snippetBody.attr('class').match(/s_[^ ]+/g);
                if (snippetClasses && snippetClasses.length) {
                    snippetClasses = '.' + snippetClasses.join('.');
                }
                const $els = $(snippetClasses).not('[data-name]').add($snippetBody);
                $els.attr('data-name', name).data('name', name);

                // Create the thumbnail
                const $thumbnail = $(`
                    <div class="oe_snippet_thumbnail">
                        <div class="oe_snippet_thumbnail_img" style="background-image: url(${el.dataset.oeThumbnail});"/>
                        <span class="oe_snippet_thumbnail_title">${name}</span>
                    </div>
                `);
                $snippet.prepend($thumbnail);

                // Create the install button (t-install feature) if necessary
                const moduleID = $snippet.data('moduleId');
                if (moduleID) {
                    el.classList.add('o_snippet_install');
                    $thumbnail.append($('<button/>', {
                        class: 'btn btn-primary o_install_btn w-100',
                        type: 'button',
                        text: _t("Install"),
                    }));
                }

                // Create the delete button for custom snippets
                if (isCustomSnippet) {
                    const btnEl = document.createElement('we-button');
                    btnEl.dataset.snippetId = $snippet.data('oeSnippetId');
                    btnEl.classList.add('o_delete_btn', 'fa', 'fa-trash', 'btn', 'o_we_hover_danger');
                    btnEl.title = _.str.sprintf(_t("Delete %s"), name);
                    $snippet.append(btnEl);
                }
            })
            .not('[data-module-id]');

        // Hide scroll if no snippets defined
        if (!this.$snippets.length) {
            this.$el.detach();
        }

        // Register the text nodes that needs to be auto-selected on click
        this._registerDefaultTexts();

        // Force non editable part to contentEditable=false
        $html.find('.o_not_editable').attr('contentEditable', false);

        // Add the computed template and make elements draggable
        this.$el.html($html);
        this.$el.append(this.customizePanel);
        this.$el.append(this.textEditorPanelEl);
        this.$el.append(this.invisibleDOMPanelEl);
        this._makeSnippetDraggable(this.$snippets);
        await this._disableUndroppableSnippets();

        this.$el.closest('.o_main_sidebar').addBack().addClass('o_loaded');
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
    _getSnippetEditor: async function ($snippet) {
        var snippetEditor = $snippet.data('snippet-editor');
        if (snippetEditor) {
            snippetEditor._resetOptionsTarget();
            return snippetEditor.__isStarted;
        }

        var $parent = globalSelector.closest($snippet.parent());
        let parentEditor;
        if ($parent.length) {
            parentEditor = await this._getSnippetEditor($parent);
        }

        // When reaching this position, after the Promise resolution, the
        // snippet editor instance might have been created by another call
        // to _getSnippetEditor... the whole logic should be improved
        // to avoid doing this here.
        if (snippetEditor) {
            return snippetEditor.__isStarted;
        }

        let editableArea = this.$editor;
        snippetEditor = new SnippetEditor(parentEditor || this,
            $snippet,
            this.templateOptions,
            $snippet.closest('[data-oe-type="html"], .oe_structure').add(editableArea),
            this,
            this.options);
        this.snippetEditors.push(snippetEditor);
        await snippetEditor.appendTo(this.$snippetEditorArea);

        return snippetEditor;
    },
    /**
     * There may be no location where some snippets might be dropped. This mades
     * them appear disabled in the menu.
     *
     * @todo make them undraggable
     * @private
     */
    _disableUndroppableSnippets: async function () {
        var self = this;
        var cache = {};

        for (const snippetDraggable of this.$snippets.toArray()) {
            var $snippetDraggable = $(snippetDraggable);
            var $snippetTemplate = $snippetDraggable.find('.oe_snippet_body');

            var isEnabled = false;
            _.each(self.templateOptions, function (option, k) {
                if (isEnabled || !($snippetTemplate.is(option.base_selector) && !$snippetTemplate.is(option.base_exclude))) {
                    return;
                }
                cache[k] = cache[k] || {
                    'drop-near': option['drop-near'] ? option['drop-near'].all().length : 0,
                    'drop-in': option['drop-in'] ? option['drop-in'].all().length : 0
                };
                isEnabled = (cache[k]['drop-near'] || cache[k]['drop-in']);
            });
            $snippetDraggable.find('.o_snippet_undroppable').remove();
            if (isEnabled) {
                $snippetDraggable.removeClass('o_disabled');
                $snippetDraggable.attr('title', '');
            } else {
                $snippetDraggable.addClass('o_disabled');
                $snippetDraggable.attr('title', _t("No location to drop in"));
                const imgEl = document.createElement('img');
                imgEl.classList.add('o_snippet_undroppable');
                imgEl.src = '/web_editor/static/src/img/snippet_disabled.svg';
                $snippetDraggable.append(imgEl);
            }
        }
    },
    /**
     * @private
     * @param {string} [search]
     */
    _filterSnippets(search) {
        const searchInputEl = this.el.querySelector('.o_snippet_search_filter_input');
        const searchInputReset = this.el.querySelector('.o_snippet_search_filter_reset');
        if (search !== undefined) {
            searchInputEl.value = search;
        } else {
            search = searchInputEl.value;
        }
        search = search.toLowerCase();
        searchInputReset.classList.toggle('d-none', !search);
        const strMatches = str => !search || str.toLowerCase().includes(search);
        for (const panelEl of this.el.querySelectorAll('.o_panel')) {
            let hasVisibleSnippet = false;
            const panelTitle = panelEl.querySelector('.o_panel_header').textContent;
            const isPanelTitleMatch = strMatches(panelTitle);
            for (const snippetEl of panelEl.querySelectorAll('.oe_snippet')) {
                const matches = (isPanelTitleMatch
                    || strMatches(snippetEl.getAttribute('name'))
                    || strMatches(snippetEl.dataset.oeKeywords || ''));
                if (matches) {
                    hasVisibleSnippet = true;
                }
                snippetEl.classList.toggle('d-none', !matches);
            }
            panelEl.classList.toggle('d-none', !hasVisibleSnippet);
        }
    },
    /**
     * @private
     * @param {Object} [options={}]
     * @returns {Object}
     */
    _getScrollOptions(options = {}) {
        return Object.assign({}, options, {
            scrollBoundaries: Object.assign({
                right: false,
            }, options.scrollBoundaries),
            jQueryDraggableOptions: Object.assign({
                appendTo: this.$editor,
                cursor: 'move',
                greedy: true,
                scroll: false,
            }, options.jQueryDraggableOptions),
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
        var dragStarted;
        var dropped;
        let scrollValue;

        const smoothScrollOptions = this._getScrollOptions({
            jQueryDraggableOptions: {
                iframeFix: true,
                handle: '.oe_snippet_thumbnail:not(.o_we_already_dragging)',
                helper: function () {
                    const dragSnip = this.cloneNode(true);
                    dragSnip.querySelectorAll('.o_delete_btn').forEach(
                        el => el.remove()
                    );
                    return dragSnip;
                },
                start: function (ev, ui) {
                    self.$el.find('.oe_snippet_thumbnail').addClass('o_we_already_dragging');
                    var $snippet = this;
                    var $baseBody = $snippet.find('.oe_snippet_body');

                    if (dragStarted) {
                        // If the previous drop are not finished, the position of the current snippet can be wrong.
                        // And JWEditor can have a mismatch for the redrawing.
                        $snippet.data('to-insert', $());
                        return;
                    }
                    dragStarted = true;

                    const $snippetToInsert = $baseBody.clone();

                    var $selectorSiblings = $();
                    var $selectorChildren = $();
                    for (const option of self.templateOptions) {
                        if ($baseBody.is(option.base_selector) && !$baseBody.is(option.base_exclude)) {
                            if (option['drop-near']) {
                                $selectorSiblings = $selectorSiblings.add(option['drop-near'].all()).filter(function () {
                                    return !$snippet[0].contains(this);
                                });
                            }
                            if (option['drop-in']) {
                                $selectorChildren = $selectorChildren.add(option['drop-in'].all()).filter(function () {
                                    return !$snippet[0].contains(this);
                                });
                            }
                        }
                    }

                    // Color-customize dynamic SVGs in dropped snippets with current theme colors.
                    [...$snippetToInsert.find('img[src^="/web_editor/shape/"]')].forEach(dynamicSvg => {
                        const colorCustomizedURL = new URL(dynamicSvg.getAttribute('src'), window.location.origin);
                        colorCustomizedURL.searchParams.forEach((key, value) => {
                            const match = key.match(/^c([1-5])$/);
                            if (match) {
                                colorCustomizedURL.searchParams.set(key, getCSSVariableValue(`o-color-${match[1]}`))
                            }
                        })
                        dynamicSvg.src = colorCustomizedURL.pathname + colorCustomizedURL.search;
                    });

                    if (!$selectorSiblings.length && !$selectorChildren.length) {
                        console.warn($snippet.find('.oe_snippet_thumbnail_title').text() + " have not insert action: data-drop-near or data-drop-in");
                        return;
                    }

                    self._enableLastEditor();
                    self._activateInsertionZones($selectorSiblings, $selectorChildren);

                    self._dragAndDropStart();

                    let $el = self.$editor;
                    if ($el[0].ownerDocument !== document) {
                        $el = $($el[0].ownerDocument.defaultView.frameElement);
                        if ($el) {
                            const offset = $el.offset();
                            const style = window.getComputedStyle($el[0]);
                            ui.helper.css({
                                marginTop: (- offset.top - parseInt(style.borderTop)) + 'px',
                                marginLeft: (- offset.left - parseInt(style.borderLeft)) + 'px',
                            });
                        }
                    }

                    $snippet.data('to-insert', $snippetToInsert);
                },
                stop: async function (ev, ui) {
                    const $snippetToInsert = this.data('to-insert');
                    $snippetToInsert.removeClass('oe_snippet_body');

                    if (!dropped && ui.position.top > 3 && ui.position.left + ui.helper.outerHeight() < self.el.getBoundingClientRect().left) {
                        var $el = $.nearest({x: ui.position.left, y: ui.position.top}, '.oe_drop_zone', {container: document.body}).first();
                        if ($el.length) {
                            scrollValue = $el.offset().top;
                            $el.after($snippetToInsert);
                            dropped = true;
                        }
                    }

                    self.$editor.find('.oe_drop_zone').remove();

                    if (dropped) {
                        var prev = $snippetToInsert.first()[0].previousSibling;
                        var next = $snippetToInsert.last()[0].nextSibling;

                        if (prev) {
                            $snippetToInsert.detach();
                            $snippetToInsert.insertAfter(prev);
                        } else if (next) {
                            $snippetToInsert.detach();
                            $snippetToInsert.insertBefore(next);
                        } else {
                            var $parent = $snippetToInsert.parent();
                            $snippetToInsert.detach();
                            $parent.prepend($snippetToInsert);
                        }

                        self._scrollToSnippet($snippetToInsert, scrollValue);

                        _.defer(async () => {
                            self.trigger_up('snippet_dropped', {$target: $snippetToInsert});

                            await self._callForEachChildSnippet($snippetToInsert, function (editor) {
                                return editor.buildSnippet();
                            });

                            const jwEditor = self.wysiwyg.editor;
                            const vNodes = await self._insertSnippet($snippetToInsert);

                            self._disableUndroppableSnippets();

                            self.dragAndDropResolve();

                            $snippetToInsert.trigger('content_changed');
                            await self._updateInvisibleDOM();

                            self.$el.find('.oe_snippet_thumbnail').removeClass('o_we_already_dragging');
                        });
                    } else {
                        $snippetToInsert.remove();
                        self.dragAndDropResolve();
                        self.$el.find('.oe_snippet_thumbnail').removeClass('o_we_already_dragging');
                    }
                    dropped = false;
                    dragStarted = false;
                },
            },
            dropzones: function () {
                return self.$editor.find('.oe_drop_zone');
            },
            over: function (ui, droppable) {
                if (!dropped) {
                    dropped = true;
                    scrollValue = $(droppable).offset().top;
                    const $snippetToInsert = this.data('to-insert');
                    $(droppable).after($snippetToInsert).addClass('d-none');
                    $snippetToInsert.removeClass('oe_snippet_body');
                }
            },
            out: function (ui, droppable) {
                const $snippetToInsert = this.data('to-insert');
                var prev = $snippetToInsert.prev();
                if (droppable === prev[0]) {
                    dropped = false;
                    $snippetToInsert.detach();
                    $(droppable).removeClass('d-none');
                    $snippetToInsert.addClass('oe_snippet_body');
                }
            },
        });
        this.draggableComponent = new SmoothScrollOnDrag(this, $snippets, this.$editor.find('#wrapwrap').addBack().last(), smoothScrollOptions);
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
    /**
     * Changes the content of the right panel and selects a tab.
     *
     * @private
     * @param {htmlString | Element | Text | Array | jQuery} [content]
     * the new content of the customizePanel
     * @param {this.tabs.VALUE} [tab='blocks'] - the tab to select
     */
    _updateRightPanelContent: function ({content, tab}) {
        clearTimeout(this._textToolsSwitchingTimeout);
        this._closeWidgets();
        tab = tab || this.tabs.BLOCKS;

        this.wysiwyg.$toolbar.detach();
        if (content) {
            while (this.customizePanel.firstChild) {
                this.customizePanel.removeChild(this.customizePanel.firstChild);
            }
            $(this.customizePanel).append(content);

            if (tab === this.tabs.OPTIONS) {
                const isImage = $(this.customizePanel).find('we-customizeblock-option.snippet-option-ImageOptimize').length > 0
                this._addJabberwockToolbar(isImage ? 'image' : 'text');
            }
        }

        if (tab === this.tabs.THEME) {
            // Ensure the toolbar container is not in the side bar when we select the themes options tab.
            $("#o_we_jw_toolbar_container").remove();
        }

        this.$('.o_snippet_search_filter').toggleClass('d-none', tab !== this.tabs.BLOCKS);
        this.$('#o_scroll').toggleClass('d-none', tab !== this.tabs.BLOCKS);
        this.customizePanel.classList.toggle('d-none', tab === this.tabs.BLOCKS);
        this.textEditorPanelEl.classList.toggle('d-none', tab !== this.tabs.OPTIONS);

        this.$('.o_we_add_snippet_btn').toggleClass('active', tab === this.tabs.BLOCKS);
        this.$('.o_we_customize_snippet_btn').toggleClass('active', tab === this.tabs.OPTIONS)
                                             .prop('disabled', tab !== this.tabs.OPTIONS);

    },
    /**
     * update the jabberwock toolbar container box.
     */
    _currentJabberwockToolbarMode: undefined,
    updateJabberwockToolbarContainer : _.debounce(function (toolbarMode) {
        if(toolbarMode !== this._currentJabberwockToolbarMode) {
            const $oldToolbar = this.wysiwyg.$toolbar.parent();
            this._addJabberwockToolbar(toolbarMode);
            $oldToolbar.remove();
        }
    }, 100),
    /**
     * Add the jabberwock toolbar.
     */
    _addJabberwockToolbar(toolbarMode = "text") {
        this._currentJabberwockToolbarMode = toolbarMode;
        const $toolbar = this.wysiwyg.$toolbar;

        let titleText = _t("Text Formatting");
        switch (toolbarMode) {
            case "image":
                titleText = _t("Image Formatting");
                break;
            case "video":
                titleText = _t("Video Formatting");
                break;
            case "picto":
                titleText = _t("Icon Formatting");
                break;
        }
        const customizeBlock = $('<WE-CUSTOMIZEBLOCK-OPTIONS id="o_we_jw_toolbar_container"/>');
        const $title = $("<we-title><span>" + titleText + "</span></we-title>");
        if (toolbarMode === "text") {
            const $removeFormatButton = $('<we-button/>', {
                class: 'fa fa-fw fa-eraser o_we_link o_we_hover_danger',
                title: 'Clear Formatting',
            })
            $removeFormatButton.on('click', () => {
                this.wysiwyg.editor.execCommand('removeFormat');
            });
            const $group = $('<we-top-button-group>');
            $group.append($removeFormatButton);
            $title.append($group);
        }
        customizeBlock.append($title);
        customizeBlock.append($toolbar);
        $(this.customizePanel).append(customizeBlock);

        $toolbar.off('click.we_oe_snippets').on('click.we_oe_snippets', 'jw-select', ev => {
            this.$el.toggleClass('o_we_backdrop', ev.currentTarget.getAttribute('aria-pressed') === 'true');
        });
    },
    /**
     * Scrolls to given snippet.
     *
     * @private
     * @param {jQuery} $el - snippet to scroll to
     * @return {Promise}
     */
    async _scrollToSnippet($el) {
        return dom.scrollTo($el[0], {extraOffset: 50});
    },
    /**
     * @private
     * @returns {HTMLElement}
     */
    _createLoadingElement() {
        const loaderContainer = document.createElement('div');
        const loader = document.createElement('i');
        const loaderContainerClassList = [
            'o_we_ui_loading',
            'd-flex',
            'justify-content-center',
            'align-items-center',
        ];
        const loaderClassList = [
            'fa',
            'fa-circle-o-notch',
            'fa-spin',
            'fa-4x',
        ];
        loaderContainer.classList.add(...loaderContainerClassList);
        loader.classList.add(...loaderClassList);
        loaderContainer.appendChild(loader);
        return loaderContainer;
    },
    /**
     * Adds the action to the mutex queue and sets a loading effect over the
     * editor to appear if the action takes too much time.
     * As soon as the mutex is unlocked, the loading effect will be removed.
     *
     * @private
     * @param {function} action
     * @param {boolean} [contentLoading=true]
     * @param {number} [delay=500]
     * @returns {Promise}
     */
    async _execWithLoadingEffect(action, contentLoading = true, delay = 500) {
        const mutexExecResult = this._mutex.exec(action);
        if (!this.loadingTimers[contentLoading]) {
            this.loadingTimers[contentLoading] = setTimeout(() => {
                this.loadingElements[contentLoading] = this._createLoadingElement();
                if (contentLoading) {
                    this.$snippetEditorArea.append(this.loadingElements[contentLoading]);
                } else {
                    this.el.appendChild(this.loadingElements[contentLoading]);
                }
            }, delay);
            this._mutex.getUnlockedDef().then(() => {
                // Note: we remove the loading element at the end of the
                // execution queue *even if subsequent actions are content
                // related or not*. This is a limitation of the loading feature,
                // the goal is still to limit the number of elements in that
                // queue anyway.
                clearTimeout(this.loadingTimers[contentLoading]);
                this.loadingTimers[contentLoading] = undefined;

                if (this.loadingElements[contentLoading]) {
                    this.loadingElements[contentLoading].remove();
                    this.loadingElements[contentLoading] = null;
                }
            });
        }
        return mutexExecResult;
    },

    /**
     * Called when a snippet will be moved in the page.
     *
     * @private
     */
    _dragAndDropStart: async function () {
        this._mutex.exec(() => {
            let dragAndDropResolve;
            const promise = new Promise(resolve => dragAndDropResolve = () => resolve());
            this.dragAndDropResolve = dragAndDropResolve;
            return promise;
        });
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
        if (ev.data.saveTarget) {
            this._setLastSnippet(ev.data.$element, ev.data.savePreview && ev.data.previewMode);
        }
        this._activateSnippet(ev.data.$element, ev.data.previewMode, ev.data.ifInactiveOptions);
    },
    /**
     * Called when a child editor asks to operate some operation on all child
     * snippet of a DOM element.
     *
     * @private
     * @param {OdooEvent} ev
     */
    _onCallForEachChildSnippet: async function (ev) {
        await this._callForEachChildSnippet(ev.data.$snippet, ev.data.callback);
        ev.data.resolve && ev.data.resolve();
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
    _onCloneSnippet: async function (ev) {
        ev.stopPropagation();
        const snippetEditor = await this._getSnippetEditor(ev.data.$snippet);
        await snippetEditor.clone();
        if (ev.data.onSuccess) {
            ev.data.onSuccess();
        }
    },
    /**
     * Called when a child editor asks to deactivate the current snippet
     * overlay.
     *
     * @private
     */
    _onDeactivateSnippet: function (ev) {
        this._enableLastEditor(ev.data.previewMode);
    },

    /**
     * Called when a snippet will be moved in the page.
     *
     * @private
     * @param {OdooEvent} ev
     */
    _onDragAndDropStart: async function (ev) {
        this._dragAndDropStart()
    },
    /**
     * Called when a snippet has moved in the page.
     *
     * @private
     * @param {OdooEvent} ev
     */
    _onDragAndDropStop: async function (ev) {
        this.dragAndDropResolve();
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
        for (const snippetEditor of this.snippetEditors) {
            snippetEditor.toggleOverlay(false);
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
                            reloadEditor: true,
                            _toMutex: true,
                        });
                    }).guardedCatch(reason => {
                        reason.event.preventDefault();
                        this.close();
                        self.displayNotification({
                            message: _.str.sprintf(_t("Could not install module <strong>%s</strong>"), name),
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
        const isVisible = await this._execWithLoadingEffect(async () => {
            const editor = await this._getSnippetEditor($snippet);
            return editor.toggleTargetVisibility();
        }, true);
        $(ev.currentTarget).find('.fa')
            .toggleClass('fa-eye', isVisible)
            .toggleClass('fa-eye-slash', !isVisible);
        if (isVisible) {
            return this._activateSnippet($snippet);
        } else {
            return this._enableLastEditor();
        }
    },
    /**
     * @private
     */
    _onBlocksTabClick: async function (ev) {
        await this._enableLastEditor();
        this._updateRightPanelContent({
            content: [],
            tab: this.tabs.BLOCKS,
        });
    },
    /**
     * @private
     */
    _onDeleteBtnClick: function (ev) {
        const $snippet = $(ev.target).closest('.oe_snippet');
        new Dialog(this, {
            size: 'medium',
            title: _t('Confirmation'),
            $content: $('<div><p>' + _t(`Are you sure you want to delete the snippet: ${$snippet.attr('name')} ?`) + '</p></div>'),
            buttons: [{
                text: _t("Yes"),
                close: true,
                classes: 'btn-primary',
                click: async () => {
                    await this._rpc({
                        model: 'ir.ui.view',
                        method: 'delete_snippet',
                        kwargs: {
                            'view_id': parseInt(ev.currentTarget.dataset.snippetId),
                            'template_key': this.options.snippets,
                        },
                    });
                    await this._loadSnippetsTemplates(true);
                },
            }, {
                text: _t("No"),
                close: true,
            }],
        }).open();
    },
    /**
     * Prevents pointer-events to change the focus when a pointer slide from
     * left-panel to the editable area.
     *
     * @private
     */
    _onMouseDown: function (ev) {
        this.$editor.addClass('o_we_no_pointer_events');
        const reenable = () => this.$editor.removeClass('o_we_no_pointer_events');
        // Use a setTimeout fallback to avoid locking the editor if the mouseup
        // is fired over an element which stops propagation for example.
        const enableTimeoutID = setTimeout(reenable, 5000);
        $(window).one('mouseup', () => {
            clearTimeout(enableTimeoutID);
            reenable();
        });
    },
    /**
     * @private
     * @param {Event}
     */
    _onContentMouseDown: function (ev) {
        const el = this.editorHelpers.elementFromPoint(ev.clientX, ev.clientY);

        const editable = el && el.closest('.note-editable');

        if (!editable || !this.$editor.is(editable) || this.lastElement === el) {
            return;
        }
        this.lastElement = el;
        setTimeout(() => {this.lastElement = false;});

        var $snippet = $(el);
        if (!$snippet.closest('we-button, we-toggler, .o_we_color_preview').length) {
            this._closeWidgets();
        }
        if ($snippet.closest(this._notActivableElementsSelector).length) {
            return;
        }
        const $oeStructure = $snippet.closest('.oe_structure');
        if ($oeStructure.length && !$oeStructure.children().length && this.$snippets) {
            // If empty oe_structure, encourage using snippets in there by
            // making them "wizz" in the panel.
            this.$snippets.odooBounce();
            return;
        }
        this._setLastSnippet($snippet);
        this._activateSnippet($snippet);
    },
    /**
     * @private
     * @param {OdooEvent} ev
     */
    _onGetSnippetVersions: function (ev) {
        const snippet = this.el.querySelector(`.oe_snippet > [data-snippet="${ev.data.snippetName}"]`);
        ev.data.onSuccess(snippet && {
            vcss: snippet.dataset.vcss,
            vjs: snippet.dataset.vjs,
            vxml: snippet.dataset.vxml,
        });
    },
    /**
     * @private
     */
    _onReloadSnippetTemplate: async function (ev) {
        await this._enableLastEditor();
        await this._loadSnippetsTemplates(true);
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
    _onRemoveSnippet: async function (ev) {
        ev.stopPropagation();
        const snippetEditor = await this._getSnippetEditor(ev.data.$snippet);
        await snippetEditor.removeSnippet();
        if (ev.data.onSuccess) {
            ev.data.onSuccess();
        }
    },
    /**
     * Saving will destroy all editors since they need to clean their DOM.
     * This has thus to be done when they are all finished doing their work.
     *
     * @private
     */
    _onSaveRequest: function (ev) {
        const data = ev.data;
        if (ev.target === this && !data._toMutex) {
            return;
        }
        delete data._toMutex;
        ev.stopPropagation();
        this._execWithLoadingEffect(() => {
            if (data.reloadEditor) {
                data.reload = false;
                const oldOnSuccess = data.onSuccess;
                data.onSuccess = async function () {
                    if (oldOnSuccess) {
                        await oldOnSuccess.call(this, ...arguments);
                    }
                    window.location.href = window.location.origin + window.location.pathname + '?enable_editor=1';
                };
            }
            this.trigger_up('request_save', data);
        }, true);
    },
    /**
     * @private
     */
    _onSnippetClick() {
        const $els = this.getEditableArea().find('.oe_structure.oe_empty').addBack('.oe_structure.oe_empty');
        for (const el of $els) {
            if (!el.children.length) {
                $(el).odooBounce('o_we_snippet_area_animation');
            }
        }
    },
    /**
     * @private
     * @param {OdooEvent} ev
     * @param {Object} ev.data
     * @param {function} ev.data.exec
     */
    _onSnippetEditionRequest: function (ev) {
        this._execWithLoadingEffect(ev.data.exec, true);
    },
    /**
     * @private
     * @param {OdooEvent} ev
     */
    _onSnippetEditorDestroyed(ev) {
        ev.stopPropagation();
        const index = this.snippetEditors.indexOf(ev.target);
        this.snippetEditors.splice(index, 1);
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
    _onSnippetRemoved: async function (ev) {
        await this._disableUndroppableSnippets();
        this._updateInvisibleDOM();
        ev.data.onFinish();
    },
    /**
     * @private
     * @param {OdooEvent} ev
     */
    _onSnippetOptionVisibilityUpdate: async function (ev) {
        if (!ev.data.show) {
            this._enableLastEditor();
        }
        await this._updateInvisibleDOM(); // Re-render to update status
    },
    /**
     * @private
     * @param {OdooEvent} ev
     */
    _onSnippetThumbnailURLRequest(ev) {
        const $snippet = this.$snippets.has(`[data-snippet="${ev.data.key}"]`);
        ev.data.onSuccess($snippet.length ? $snippet[0].dataset.oeThumbnail : '');
    },
    /**
     * @private
     */
    _onSummernoteToolsUpdate(ev) {
        if (!this._textToolsSwitchingEnabled) {
            return;
        }
        if (!$.summernote.core.range.create()) {
            // Sometimes not enough...
            return;
        }
        this.textEditorPanelEl.classList.add('d-block');
        const hasVisibleButtons = !!$(this.textEditorPanelEl).find('.btn:visible').length;
        this.textEditorPanelEl.classList.remove('d-block');
        if (!hasVisibleButtons) {
            // Ugly way to detect that summernote was updated but there is no
            // visible text tools.
            return;
        }
        // Only switch tab without changing content (_updateRightPanelContent
        // make text tools visible only on that specific tab). Also do it with
        // a slight delay to avoid flickering doing it twice.
        clearTimeout(this._textToolsSwitchingTimeout);
        this._textToolsSwitchingTimeout = setTimeout(() => {
            this._updateRightPanelContent({tab: this.tabs.OPTIONS});
        }, 250);
    },
    /**
     * @private
     * @param {OdooEvent} ev
     */
    _onUpdateCustomizeElements: function (ev) {
        this._updateRightPanelContent({
            content: ev.data.customize$Elements,
            tab: ev.data.customize$Elements.length ? this.tabs.OPTIONS : this.tabs.BLOCKS,
        });
    },
    /**
     * Called when an user value widget is being opened -> close all the other
     * user value widgets of all editors + add backdrop.
     */
    _onUserValueWidgetOpening: function () {
        this._closeWidgets();
        this.el.classList.add('o_we_backdrop');
    },
    /**
     * Called when an user value widget is being closed -> rely on the fact only
     * one widget can be opened at a time: remove the backdrop.
     */
    _onUserValueWidgetClosing: function () {
        this.el.classList.remove('o_we_backdrop');
    },
    /**
     * Called when search input value changed -> adapts the snippets grid.
     *
     * @private
     */
    _onSnippetSearchInput: function () {
        this._filterSnippets();
    },
    /**
     * Called on snippet search filter reset -> clear input field search.
     *
     * @private
     */
    _onSnippetSearchResetClick: function () {
        this._filterSnippets('');
    },

    /**
     * Retrieve the relative position of an element.
     * An element's position is 'BEFORE', 'AFTER' or 'INSIDE' another element
     * (in that order of priority).
     * Eg: the element is located before the node `a` -> return [`a`, 'BEFORE'].
     *
     * @param {JQuery} $snippet
     * @returns {[Node, 'BEFORE'|'AFTER'|'INSIDE']}
     */
    _getRelativePosition(element) {
        let currentNode = element.nextSibling;
        while (currentNode) {
            const nodes = this.editorHelpers.getNodes(currentNode);
            const node = nodes && nodes[0];
            if (node) {
                return [currentNode, 'BEFORE'];
            }
            currentNode = currentNode.nextSibling;
        }
        currentNode = element.previousSibling;
        while (currentNode) {
            const nodes = this.editorHelpers.getNodes(currentNode);
            const node = nodes && nodes[0];
            if (node) {
                return [currentNode, 'AFTER'];
            }
            currentNode = currentNode.previousSibling;
        }
        currentNode = element.parentElement;
        while (currentNode) {
            const nodes = this.editorHelpers.getNodes(currentNode);
            const node = nodes && nodes[0];
            if (node) {
                return [currentNode, 'INSIDE'];
            }
            currentNode = currentNode.parentElement;
        }
    },
    /**
     * Insert a snippet at range.
     *
     * @param {JQuery} $snippet
     * @returns {VNode[]}
     */

    _insertSnippet: async function ($snippet) {
        const jwEditor = this.wysiwyg.editor;
        let result;
        const insertSnippet = async (context) => {
            const layout = jwEditor.plugins.get(this.JWEditorLib.Layout);
            const domLayout = layout.engines.dom;
            domLayout.markForRedraw(new Set($snippet.find('*').contents().addBack().add($snippet).get()));
            const position = this._getRelativePosition($snippet[0]);
            if (!position) {
                throw new Error("Could not find a place to insert the snippet.");
            }
            result = await this.editorHelpers.insertHtml(context, $snippet[0].outerHTML, position[0], position[1]);
        };
        await jwEditor.execCommand(insertSnippet);
        return result;
    },
    /**
     * On click on save button.
     */
    _onSaveClick: function() {
        this.wysiwyg.saveContent();
    },
    /**
     * On click on discard button.
     */
    _onDiscardClick: function() {
        this.wysiwyg.discardEditions();
    },
    /**
     * On click on discard button.
     */
    _onMobilePreviewClick: async function() {
        await this.wysiwyg.editor.execCommand('toggleDevicePreview', { device: 'mobile' });
        await new Promise(r => setTimeout(r)); // Wait browser redrawing (because the commands use microtask and not setTimeout)
        const $iframe = this.$el.closest('.wrap_editor').find('iframe[name="jw-iframe"]');
        if ($iframe.length) {
            config.device.isMobile = true;
            config.device.bus.trigger('size_changed', 0);
        } else {
            config.device.isMobile = config.device.size_class <= config.device.SIZES.SM;
            config.device.bus.trigger('size_changed', config.device.size_class);
        }
    },
    /**
     * Set the last snippet activated.
     */
    _setLastSnippet($snippet, preview = false) {
        this._removeLastSnippetActivated();
        $snippet[0].classList.add('o_we_last_snippet_activated');
        if (preview) $snippet[0].classList.add('o_we_last_snippet_preview');
    },
    /**
     * Remove the last snippet that has been activated.
     */
    async _removeLastSnippetActivated() {
        const classesToRemove = ['o_we_last_snippet_activated', 'o_we_last_snippet_preview'];
        const $lastSnippet = this.$editor.find('.o_we_last_snippet_activated');
        $lastSnippet.removeClass(classesToRemove);
        if ($lastSnippet.length) {
            // loop in case the class has been duplicated (e.g. cloned)
            const removeLastSnippetActivated = async (context) => {
                for (const lastSnippet of $lastSnippet.toArray()) {
                    await this.editorHelpers.removeClass(context, lastSnippet, classesToRemove);
                }
            }
            await this.wysiwyg.editor.execCommand(removeLastSnippetActivated);
        }
    },
});

return {
    SnippetsMenu: SnippetsMenu,
    globalSelector: globalSelector,
};
});
