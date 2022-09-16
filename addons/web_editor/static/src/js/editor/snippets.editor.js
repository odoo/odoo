odoo.define('web_editor.snippet.editor', function (require) {
'use strict';

var concurrency = require('web.concurrency');
var core = require('web.core');
var Dialog = require('web.Dialog');
var dom = require('web.dom');
const {Markup, sprintf, confine} = require('web.utils');
var Widget = require('web.Widget');
var options = require('web_editor.snippets.options');
const {ColorPaletteWidget} = require('web_editor.ColorPalette');
const SmoothScrollOnDrag = require('web/static/src/js/core/smooth_scroll_on_drag.js');
const {getCSSVariableValue} = require('web_editor.utils');
const gridUtils = require('@web_editor/js/common/grid_layout_utils');
const QWeb = core.qweb;

var _t = core._t;

let cacheSnippetTemplate = {};

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

function firstChild(node) {
    while (node.firstChild) {
        node = node.firstChild;
    }
    return node;
}
function lastChild(node) {
    while (node.lastChild) {
        node = node.lastChild;
    }
    return node;
}
function nodeLength(node) {
    if (node.nodeType === Node.TEXT_NODE) {
        return node.nodeValue.length;
    } else {
        return node.childNodes.length;
    }
}


$.fn.extend({
    focusIn: function () {
        if (this.length) {
            const selection = this[0].ownerDocument.getSelection();
            selection.removeAllRanges();

            const range = new Range();
            const node = firstChild(this[0]);
            range.setStart(node, 0);
            range.setEnd(node, 0);
            selection.addRange(range);
        }
        return this;
    },
    focusInEnd: function () {
        if (this.length) {
            const selection = this[0].ownerDocument.getSelection();
            selection.removeAllRanges();

            const range = new Range();
            const node = lastChild(this[0]);
            const length = nodeLength(node);

            range.setStart(node, length);
            range.setEnd(node, length);
            selection.addRange(range);
        }
        return this;
    },
    selectContent: function () {
        if (this.length && !this[0].hasChildNodes()) {
            return this.selectElement();
        }
        if (this.length) {
            const selection = this[0].ownerDocument.getSelection();
            selection.removeAllRanges();

            const range = new Range();
            range.setStart(this[0].firstChild, 0);
            range.setEnd(this[0].lastChild, this[0].lastChild.length);
            selection.addRange(range);
        }
        return this;
    },
    selectElement: function () {
        if (this.length) {
            const selection = this[0].ownerDocument.getSelection();
            selection.removeAllRanges();

            const element = this[0];
            const parent = element.parentNode;
            const offsetStart = Array.from(parent.childNodes).indexOf(element);

            const range = new Range();
            range.setStart(parent, offsetStart);
            range.setEnd(parent, offsetStart + 1);
            selection.addRange(range);
        }
        return this;
    },
});

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
    events: {
        'click .oe_snippet_remove': '_onRemoveClick',
        'wheel': '_onMouseWheel',
        'click .o_send_back': '_onSendBackClick',
        'click .o_bring_front': '_onBringFrontClick',
    },
    custom_events: {
        'option_update': '_onOptionUpdate',
        'user_value_widget_request': '_onUserValueWidgetRequest',
        'snippet_option_visibility_update': '_onSnippetOptionVisibilityUpdate',
    },
    layoutElementsSelector: [
        '.o_we_shape',
        '.o_we_bg_filter',
    ].join(','),

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
        this.$scrollingElement = $().getScrollingElement(this.$editable[0].ownerDocument);
        if (!this.$scrollingElement[0]) {
            this.$scrollingElement = $(this.ownerDocument).find('.o_editable');
        }
        this.displayOverlayOptions = false;
        this._$toolbarContainer = $();

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
        this.isTargetMovable = this.isTargetParentEditable && this.isTargetMovable && !this.$target.hasClass('oe_unmovable');
        this.isTargetRemovable = this.isTargetParentEditable && !this.$target.parent().is('[data-oe-type="image"]') && !this.$target.hasClass('oe_unremovable');
        this.displayOverlayOptions = this.displayOverlayOptions || this.isTargetMovable || !this.isTargetParentEditable;

        // Initialize move/clone/remove buttons
        if (this.isTargetMovable) {
            this.dropped = false;
            const smoothScrollOptions = this.options.getScrollOptions({
                jQueryDraggableOptions: {
                    cursorAt: {
                        left: 10,
                        top: 10
                    },
                    handle: '.o_move_handle',
                    helper: () => {
                        var $clone = this.$el.clone().css({width: '24px', height: '24px', border: 0});
                        $clone.appendTo(this.$el[0].ownerDocument.body).removeClass('d-none');
                        return $clone;
                    },
                    start: this._onDragAndDropStart.bind(this),
                    stop: (...args) => {
                        // Delay our stop handler so that some wysiwyg handlers
                        // which occur on mouseup (and are themself delayed) are
                        // executed first (this prevents the library to crash
                        // because our stop handler may change the DOM).
                        setTimeout(() => {
                            this._onDragAndDropStop(...args);
                        }, 0);
                    },
                    refreshPositions: true, // So the dropzone expands when its size increases.
                },
            });
            const modalAncestorEl = this.$target[0].closest('.modal');
            const $scrollable = modalAncestorEl && $(modalAncestorEl)
                || (this.options.wysiwyg.snippetsMenu && this.options.wysiwyg.snippetsMenu.$scrollable)
                || (this.$scrollingElement.length && this.$scrollingElement)
                || $().getScrollingElement(this.ownerDocument);
            this.draggableComponent = new SmoothScrollOnDrag(this, this.$el, $scrollable, smoothScrollOptions);
        } else {
            this.$('.o_overlay_move_options').addClass('d-none');
            $customize.find('.oe_snippet_clone').addClass('d-none');
        }

        if (!this.isTargetRemovable) {
            this.$el.add($customize).find('.oe_snippet_remove').addClass('d-none');
        }

        var _animationsCount = 0;
        var postAnimationCover = _.throttle(() => {
            this.trigger_up('cover_update', {
                overlayVisible: true,
            });
        }, 100);
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
        // Before actually destroying a snippet editor, notify the parent
        // about it so that it can update its list of alived snippet editors.
        this.trigger_up('snippet_editor_destroyed');
        if (this.$optionsSection) {
            this.$optionsSection.remove();
        }
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
            await this.styles[i].onBuilt();
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
        if (!this.styles || !this.areOptionsShown()) {
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
        if (!this.isShown() || !this.$target.length) {
            return;
        }

        const $modal = this.$target.find('.modal:visible');
        const $target = $modal.length ? $modal : this.$target;
        const targetEl = $target[0];

        // Check first if the target is still visible, otherwise we have to
        // hide it. When covering all element after scroll for instance it may
        // have been hidden (part of an affixed header for example) or it may
        // be outside of the viewport (the whole header during an effect for
        // example).
        const rect = targetEl.getBoundingClientRect();
        const vpWidth = targetEl.ownerDocument.defaultView.innerWidth || document.documentElement.clientWidth;
        const vpHeight = targetEl.ownerDocument.defaultView.innerHeight || document.documentElement.clientHeight;
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
        if (!isInViewport || !hasSize || !this.$target.is(`:visible`)) {
            this.toggleOverlayVisibility(false);
            return;
        }

        const transform = window.getComputedStyle(targetEl).getPropertyValue('transform');
        const transformOrigin = window.getComputedStyle(targetEl).getPropertyValue('transform-origin');
        targetEl.classList.add('o_transform_removal');

        // Now cover the element
        const offset = $target.offset();

        // If the target is in an iframe, we need the iframe offset.
        const targetWindow = $target[0].ownerDocument.defaultView;
        const editorWindow = this.$el[0].ownerDocument.defaultView;
        if (targetWindow.frameElement && targetWindow !== editorWindow) {
            const { x, y } = targetWindow.frameElement.getBoundingClientRect();
            offset.left += x;
            offset.top += y;
        }

        var manipulatorOffset = this.$el.parent().offset();
        offset.top -= manipulatorOffset.top;
        offset.left -= manipulatorOffset.left;
        this.$el.css({
            width: $target.outerWidth(),
            height: $target.outerHeight(),
            left: offset.left,
            top: offset.top,
            transform,
            'transform-origin': transformOrigin,
        });
        this.$('.o_handles').css('height', $target.outerHeight());

        targetEl.classList.remove('o_transform_removal');

        const editableOffsetTop = this.$editable.offset().top - manipulatorOffset.top;
        this.$el.toggleClass('o_top_cover', offset.top - editableOffsetTop < 25);
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
        if (this.$target.is('img')) {
            return _t("Image");
        }
        if (this.$target.is('.fa')) {
            return _t("Icon");
        }
        if (this.$target.is('.media_iframe_video')) {
            return _t("Video");
        }
        if (this.$target.parent('.row').length) {
            return _t("Column");
        }
        if (this.$target.is('#wrapwrap > main')) {
            return _t("Page Options");
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
        return (this.$target[0].dataset.invisible !== '1');
    },
    /**
     * Removes the associated snippet from the DOM and destroys the associated
     * editor (itself).
     *
     * @param {boolean} [shouldRecordUndo=true]
     * @returns {Promise}
     */
    removeSnippet: async function (shouldRecordUndo = true) {
        this.options.wysiwyg.odooEditor.unbreakableStepUnactive();
        this.toggleOverlay(false);
        await this.toggleOptions(false);
        // If it is an invisible element, we must close it before deleting it
        // (e.g. modal).
        await this.toggleTargetVisibility(!this.$target.hasClass('o_snippet_invisible'));
        this.trigger_up('will_remove_snippet', {$target: this.$target});

        // Call the onRemove of all internal options
        await new Promise(resolve => {
            this.trigger_up('call_for_each_child_snippet', {
                $snippet: this.$target,
                callback: async function (editor, $snippet) {
                    for (var i in editor.styles) {
                        await editor.styles[i].onRemove();
                    }
                },
                onSuccess: resolve,
            });
        });

        // TODO this should probably be awaited but this is not possible right
        // now as removeSnippet can be called in a locked editor mutex context
        // and would thus produce a deadlock. Also, this awaited
        // 'activate_snippet' call would allow to remove the 'toggleOverlay' and
        // 'toggleOptions' calls at the start of this function.
        // TODO also to be checked: this not being awaited, the DOM is removed
        // first, destroying the related editors and not calling onBlur... to
        // check if this has always been like this or not and this should be
        // unit tested.
        let parent = this.$target[0].parentElement;
        let nextSibling = this.$target[0].nextElementSibling;
        while (nextSibling && nextSibling.matches('.o_snippet_invisible')) {
            nextSibling = nextSibling.nextElementSibling;
        }
        let previousSibling = this.$target[0].previousElementSibling;
        while (previousSibling && previousSibling.matches('.o_snippet_invisible')) {
            previousSibling = previousSibling.previousElementSibling;
        }
        if ($(parent).is('.o_editable:not(body)')) {
            // If we target the editable, we want to reset the selection to the
            // body. If the editable has options, we do not want to show them.
            parent = $(parent).closest('body');
        }
        const activateSnippetProm = new Promise(resolve => {
            this.trigger_up('activate_snippet', {
                $snippet: $(previousSibling || nextSibling || parent),
                onSuccess: resolve,
            });
        });

        // Actually remove the snippet and its option UI.
        var $parent = this.$target.parent();
        this.$target.find('*').addBack().each((index, el) => {
            const tooltip = Tooltip.getInstance(el);
            if (tooltip) {
                tooltip.dispose();
            }
        });
        this.$target.remove();
        this.$el.remove();

        // Resize the grid to have the correct row count.
        // Must be done here and not in a dedicated onRemove method because
        // onRemove is called before actually removing the element and it
        // should be the case in order to resize the grid.
        if (this.$target[0].classList.contains('o_grid_item')) {
            gridUtils._resizeGrid($parent[0]);
        }

        var node = $parent[0];
        if (node && node.firstChild) {
            if (!node.firstChild.tagName && node.firstChild.textContent === ' ') {
                node.removeChild(node.firstChild);
            }
        }

        // Potentially remove ancestors (like when removing the last column of a
        // snippet).
        if ($parent.closest(':data("snippet-editor")').length) {
            const isEmptyAndRemovable = ($el, editor) => {
                editor = editor || $el.data('snippet-editor');
                const isEmpty = $el.text().trim() === ''
                    && $el.children().toArray().every(el => {
                        // Consider layout-only elements (like bg-shapes) as empty
                        return el.matches(this.layoutElementsSelector);
                    });
                return isEmpty && !$el.hasClass('oe_structure') && !$el.hasClass('oe_unremovable')
                    && !$el.parent().hasClass('carousel-item')
                    && (!editor || editor.isTargetParentEditable);
            };

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
                // TODO maybe this should be part of the actual Promise being
                // returned by the function ?
                setTimeout(() => editor.removeSnippet());
            }
        }

        // Clean editor if they are image or table in deleted content
        this.$body.find('.note-control-selection').hide();
        this.$body.find('.o_table_handler').remove();

        this.trigger_up('snippet_removed');
        // FIXME that whole Promise should be awaited before the DOM removal etc
        // as explained above where it is defined. However, it is critical to at
        // least await it before destroying the snippet editor instance
        // otherwise the logic of activateSnippet gets messed up.
        // FIXME should not this call _destroyEditor ?
        activateSnippetProm.then(() => this.destroy());
        $parent.trigger('content_changed');

        // TODO Page content changed, some elements may need to be adapted
        // according to it. While waiting for a better way to handle that this
        // window trigger will handle most cases.
        $(window).trigger('resize');

        if (shouldRecordUndo) {
            this.options.wysiwyg.odooEditor.historyStep();
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
            if (!this.displayOverlayOptions) {
                this.$el.find('.o_overlay_options_wrap').addClass('o_we_hidden_overlay_options');
            }
        }

        // Show/hide overlay in preview mode or not
        this.$el.toggleClass('oe_active', show);
        this.cover();
        this.toggleOverlayVisibility(show);
    },
    /**
     * Updates the UI of the editor (+ parent) options and call onFocus/onBlur
     * if necessary. The UI jquery elements to display are returned, it is up
     * to the caller to actually display them or not.
     *
     * @param {boolean} show
     * @returns {Promise<jQuery[]>}
     */
    async toggleOptions(show) {
        if (!this.$el) {
            return [];
        }

        if (this.areOptionsShown() === show) {
            return null;
        }

        // All onFocus before all ui updates as the onFocus of an option might
        // affect another option (like updating the $target)
        const editorUIsToUpdate = [];
        const focusOrBlur = show
            ? async (editor, options) => {
                for (const opt of options) {
                    await opt.onFocus();
                }
                editorUIsToUpdate.push(editor);
            }
            : async (editor, options) => {
                for (const opt of options) {
                    await opt.onBlur();
                }
            };
        for (const $el of this._customize$Elements) {
            const editor = $el.data('editor');
            const styles = _.chain(editor.styles)
                .values()
                .sortBy('__order')
                .value();

            await focusOrBlur(editor, styles);
        }
        await Promise.all(editorUIsToUpdate.map(editor => editor.updateOptionsUI()));
        await Promise.all(editorUIsToUpdate.map(editor => editor.updateOptionsUIVisibility()));

        return this._customize$Elements;
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
     * @param {boolean} [show=false]
     */
    toggleOverlayVisibility: function (show) {
        if (this.$el && !this.scrollingTimeout) {
            this.$el.toggleClass('o_overlay_hidden', (!show || this.$target[0].matches('.o_animating:not(.o_animate_on_scroll)')) && this.isShown());
        }
    },
    /**
     * Updates the UI of all the options according to the status of their
     * associated editable DOM. This does not take care of options *visibility*.
     * For that @see updateOptionsUIVisibility, which should called when the UI
     * is up-to-date thanks to the function here, as the visibility depends on
     * the UI's status.
     *
     * @returns {Promise}
     */
    async updateOptionsUI() {
        const proms = Object.values(this.styles).map(opt => {
            return opt.updateUI({noVisibility: true});
        });
        return Promise.all(proms);
    },
    /**
     * Updates the visibility of the UI of all the options according to the
     * status of their associated dependencies and related editable DOM status.
     *
     * @returns {Promise}
     */
    async updateOptionsUIVisibility() {
        const proms = Object.values(this.styles).map(opt => {
            return opt.updateUIVisibility();
        });
        return Promise.all(proms);
    },
    /**
     * Clones the current snippet.
     *
     * @param {boolean} recordUndo
     */
    clone: async function (recordUndo) {
        this.trigger_up('snippet_will_be_cloned', {$target: this.$target});

        var $clone = this.$target.clone(false);

        this.$target.after($clone);

        if (recordUndo) {
            this.options.wysiwyg.odooEditor.historyStep(true);
        }
        await new Promise(resolve => {
            this.trigger_up('call_for_each_child_snippet', {
                $snippet: $clone,
                callback: function (editor, $snippet) {
                    for (var i in editor.styles) {
                        editor.styles[i].onClone({
                            isCurrent: ($snippet.is($clone)),
                        });
                    }
                },
                onSuccess: resolve,
            });
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
        const $optionsSectionBtnGroup = $optionsSection.find('we-top-button-group');
        $optionsSectionBtnGroup.contents().each((i, node) => {
            if (node.nodeType === Node.TEXT_NODE) {
                node.parentNode.removeChild(node);
            }
        });
        this.$optionsSection = $optionsSection;
        $optionsSection.on('mouseenter', this._onOptionsSectionMouseEnter.bind(this));
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
            if (val.data.string) {
                $optionsSection[0].querySelector('we-title > span').textContent = val.data.string;
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

            if (option.forceNoDeleteButton) {
                this.$el.add($optionsSection).find('.oe_snippet_remove').addClass('d-none');
            }

            if (option.displayOverlayOptions) {
                this.displayOverlayOptions = true;
            }

            return option.appendTo(document.createDocumentFragment());
        });

        this.isTargetMovable = (this.selectorSiblings.length > 0 || this.selectorChildren.length > 0);

        this.$el.find('[data-bs-toggle="dropdown"]').dropdown();

        return Promise.all(defs).then(async () => {
            const options = _.sortBy(this.styles, '__order');
            const firstOptions = [];
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
    /**
     * Returns false if the element matches a snippet block that cannot be
     * dropped in a sanitized HTML field or a string representing a specific
     * reason. Returns true if no such issue exists.
     *
     * @param {Element} el
     * @return {boolean|str} str indicates a specific type of forbidden sanitization
     */
    _canBeSanitizedUnless(el) {
        let result = true;
        for (const snippetEl of [el, ...el.querySelectorAll('[data-snippet]')]) {
            this.trigger_up('find_snippet_template', {
                snippet: snippetEl,
                callback: function (snippetTemplate) {
                    const forbidSanitize = snippetTemplate.dataset.oeForbidSanitize;
                    if (forbidSanitize) {
                        result = forbidSanitize === 'form' ? 'form' : false;
                    }
                },
            });
            // If some element in the block is already fully non-sanitizable,
            // the whole block cannot be sanitized.
            if (!result) {
                break;
            }
        }
        return result;
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
        this.trigger_up('drag_and_drop_start');
        this.options.wysiwyg.odooEditor.automaticStepUnactive();
        var self = this;

        // Number of grid columns and rows in the grid item (BS column).
        let columnColCount;
        let columnRowCount;
        const rowEl = this.$target[0].parentNode;
        if (rowEl.classList.contains('row') && this.options.isWebsite) {
            // Toggle grid mode if it is not already on.
            if (!rowEl.classList.contains('o_grid_mode')) {
                const containerEl = rowEl.parentNode;
                gridUtils._toggleGridMode(containerEl);
            }

            this.dragState = {};
            // Computing the moving column width and height in terms of columns
            // and rows.
            const columnStart = self.$target[0].style.gridColumnStart;
            const columnEnd = self.$target[0].style.gridColumnEnd;
            const rowStart = self.$target[0].style.gridRowStart;
            const rowEnd = self.$target[0].style.gridRowEnd;

            columnColCount = columnEnd - columnStart;
            columnRowCount = rowEnd - rowStart;
            this.dragState.columnColCount = columnColCount;
            this.dragState.columnRowCount = columnRowCount;

            // Deactivate the snippet so the overlay doesn't show.
            this.trigger_up('deactivate_snippet', {$snippet: self.$target});
            // Storing the current grid and grid area to use them for the
            // history.
            this.dragState.previousGrid = rowEl;
            this.dragState.prevGridArea = self.$target[0].style.gridArea;

            // Reload the images.
            gridUtils._reloadLazyImages(this.$target[0]);
        }

        const isPopup = this.$target[0].closest('div.s_popup');

        this.dropped = false;
        this._dropSiblings = {
            prev: self.$target.prev()[0],
            next: self.$target.next()[0],
        };
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
        const canBeSanitizedUnless = this._canBeSanitizedUnless(this.$target[0]);

        // Remove the siblings that belong to a snippet in grid mode
        // and put the identified grid mode snippets in their own "selector".
        const selectorGrids = new Set();
        if (this.$target[0].classList.contains('o_grid_item')) {
            if ($selectorSiblings) {
                // Looping backwards because elements are removed, so the
                // indexes are not lost.
                for (let i = $selectorSiblings.length - 1; i >= 0; i--) {
                    if (isPopup && !$selectorSiblings[i].closest('div.s_popup')) {
                        // Removing the siblings that are outside the popup if
                        // the grid item is in a popup.
                        $selectorSiblings.splice(i, 1);
                    } else {
                        const gridSnippet = $selectorSiblings[i].closest('div.o_grid_mode');
                        if (gridSnippet) {
                            $selectorSiblings.splice(i, 1);
                            selectorGrids.add(gridSnippet);
                        }
                    }
                }
            }
        }

        this.trigger_up('activate_snippet', {$snippet: this.$target.parent()});
        this.trigger_up('activate_insertion_zones', {
            $selectorSiblings: $selectorSiblings,
            $selectorChildren: $selectorChildren,
            canBeSanitizedUnless: canBeSanitizedUnless,
            selectorGrids: selectorGrids,
        });

        this.$body.addClass('move-important');

        this.$dropZones = this.$editable.find('.oe_drop_zone');
        if (!canBeSanitizedUnless) {
            this.$dropZones = this.$dropZones.not('[data-oe-sanitize] .oe_drop_zone');
        } else if (canBeSanitizedUnless === 'form') {
            this.$dropZones = this.$dropZones.not('[data-oe-sanitize][data-oe-sanitize!="allow_form"] .oe_drop_zone');
        }
        this.$dropZones.droppable({
            over: function () {
                if (self.dropped) {
                    self.$target.detach();
                    $('.oe_drop_zone').removeClass('invisible');
                }
                self.dropped = true;
                const $dropzone = $(this).first().after(self.$target);
                $dropzone.addClass('invisible');

                if ($dropzone[0].classList.contains('oe_grid_zone')) {
                    // Case where the column we are dragging is over a grid
                    // dropzone.
                    const rowEl = $dropzone[0].parentNode;

                    // Creating the drag helper.
                    const dragHelperEl = document.createElement('div');
                    dragHelperEl.classList.add('o_we_drag_helper');
                    dragHelperEl.style.gridArea = `1 / 1 / ${1 + columnRowCount} / ${1 + columnColCount}`;
                    rowEl.append(dragHelperEl);

                    // Creating the background grid and updating the dropzone
                    // (in the case where the column over the dropzone is
                    // bigger than the grid).
                    const backgroundGridEl = gridUtils._addBackgroundGrid(rowEl, columnRowCount);
                    const rowCount = Math.max(rowEl.dataset.rowCount, columnRowCount);
                    $dropzone[0].style.gridRowEnd = rowCount + 1;

                    // Setting the background grid, the moving grid item and
                    // the drag helper z-indexes so they are in front of the
                    // other elements and in this order.
                    gridUtils._setElementToMaxZindex(backgroundGridEl, rowEl);
                    gridUtils._setElementToMaxZindex(self.$target[0], rowEl);
                    gridUtils._setElementToMaxZindex(dragHelperEl, rowEl);

                    // Setting the column height and width to keep its size
                    // when the grid-area is removed (as it prevents it from
                    // moving with the mouse).
                    const gridProp = gridUtils._getGridProperties(rowEl);
                    const columnHeight = columnRowCount * (gridProp.rowSize + gridProp.rowGap) - gridProp.rowGap;
                    const columnWidth = columnColCount * (gridProp.columnSize + gridProp.columnGap) - gridProp.columnGap;
                    self.$target[0].style.height = columnHeight + 'px';
                    self.$target[0].style.width = columnWidth + 'px';
                    self.$target[0].style.position = 'absolute';
                    self.$target[0].style.removeProperty('grid-area');
                    rowEl.style.position = 'relative';

                    // Storing useful information and adding an event listener.
                    self.dragState.startingHeight = rowEl.clientHeight;
                    self.dragState.currentHeight = rowEl.clientHeight;
                    self.dragState.dragHelperEl = dragHelperEl;
                    self.dragState.backgroundGridEl = backgroundGridEl;
                    self.dragState.dropzoneEl = $dropzone[0];
                    self.onDragMove = self._onDragMove.bind(self);
                    document.body.addEventListener('mousemove', self.onDragMove, false);
                }
            },
            out: function () {
                const dropzoneEl = this;
                const rowEl = dropzoneEl.parentNode;
                if (rowEl.classList.contains('o_grid_mode')) {
                    // Removing the listener + cleaning.
                    document.body.removeEventListener('mousemove', self.onDragMove, false);
                    gridUtils._gridCleanUp(rowEl, self.$target[0]);
                    self.$target[0].style.removeProperty('z-index');

                    // Removing the drag helper and the background grid and
                    // resizing the grid and the dropzone.
                    self.dragState.dragHelperEl.remove();
                    self.dragState.backgroundGridEl.remove();
                    gridUtils._resizeGrid(rowEl);
                    const rowCount = parseInt(rowEl.dataset.rowCount);
                    dropzoneEl.style.gridRowEnd = Math.max(rowCount + 1, 1);
                }

                var prev = self.$target.prev();
                if (this === prev[0]) {
                    self.dropped = false;
                    self.$target.detach();
                    $(this).removeClass('invisible');
                }
            },
        });

        // Trigger a scroll on the draggable element so that jQuery updates
        // the position of the drop zones.
        self.draggableComponent.$scrollTarget.on('scroll.scrolling_element', function () {
            self.$el.trigger('scroll');
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
        this.options.wysiwyg.odooEditor.automaticStepActive();
        this.options.wysiwyg.odooEditor.automaticStepSkipStack();
        this.options.wysiwyg.odooEditor.unbreakableStepUnactive();

        const rowEl = this.$target[0].parentNode;
        if (rowEl && rowEl.classList.contains('o_grid_mode')) {
            // Case when dropping the column in a grid.

            // Removing the event listener.
            document.body.removeEventListener('mousemove', this.onDragMove, false);

            // Defining the column grid area with its position.
            const gridProp = gridUtils._getGridProperties(rowEl);

            const top = parseFloat(this.$target[0].style.top);
            const left = parseFloat(this.$target[0].style.left);

            const rowStart = Math.round(top / (gridProp.rowSize + gridProp.rowGap)) + 1;
            const columnStart = Math.round(left / (gridProp.columnSize + gridProp.columnGap)) + 1;
            const rowEnd = rowStart + this.dragState.columnRowCount;
            const columnEnd = columnStart + this.dragState.columnColCount;

            this.$target[0].style.gridArea = `${rowStart} / ${columnStart} / ${rowEnd} / ${columnEnd}`;

            // Cleaning, removing the drag helper and the background grid and
            // resizing the grid.
            gridUtils._gridCleanUp(rowEl, this.$target[0]);
            this.dragState.dragHelperEl.remove();
            this.dragState.backgroundGridEl.remove();
            gridUtils._resizeGrid(rowEl);

            // Setting the z-index to the maximum of the grid.
            gridUtils._setElementToMaxZindex(this.$target[0], rowEl);
        } else if (this.$target[0].classList.contains('o_grid_item') && this.dropped) {
            // Case when dropping a grid item in a non-grid dropzone.
            this.$target[0].classList.remove('o_grid_item');
            this.$target[0].style.removeProperty('grid-area');
        }

        // TODO lot of this is duplicated code of the d&d feature of snippets
        if (!this.dropped) {
            const { nearest } = this.$body[0].ownerDocument.defaultView.$;
            let $el = nearest({x: ui.position.left, y: ui.position.top}, '.oe_drop_zone', {container: document.body}).first();
            // Some drop zones might have been disabled.
            $el = $el.filter(this.$dropZones);
            if ($el.length) {
                // If the column is not dropped inside a dropzone.
                if (this.$target[0].classList.contains('o_grid_item')) {
                    if ($el[0].classList.contains('oe_grid_zone')) {
                        // Case when a column is dropped near a grid.
                        // Placing it in the top left corner.
                        this.$target[0].style.gridArea = `1 / 1 / ${1 + this.dragState.columnRowCount} / ${1 + this.dragState.columnColCount}`;
                        const rowEl = $el[0].parentNode;
                        const rowCount = Math.max(rowEl.dataset.rowCount, 1 + this.dragState.columnRowCount);
                        rowEl.dataset.rowCount = rowCount;

                        // Setting the z-index to the maximum of the grid.
                        gridUtils._setElementToMaxZindex(this.$target[0], rowEl);
                    } else {
                        // Case when a column is dropped near a non-grid dropzone.
                        this.$target[0].classList.remove('o_grid_item');
                        this.$target[0].style.removeProperty('z-index');
                    }
                }

                $el.after(this.$target);
                this.dropped = true;
            }
        }

        this.$dropZones.droppable('destroy');
        this.$editable.find('.oe_drop_zone').remove();

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

        this.options.wysiwyg.odooEditor.observerActive('dragAndDropMoveSnippet');
        if (this.dropped) {
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
        this.draggableComponent.$scrollTarget.off('scroll.scrolling_element');
        const samePositionAsStart = this.$target[0].classList.contains('o_grid_item')
            ? (this.$target[0].parentNode === this.dragState.previousGrid
                && this.$target[0].style.gridArea === this.dragState.prevGridArea)
            : this._dropSiblings.prev === this.$target.prev()[0] && this._dropSiblings.next === this.$target.next()[0];
        if (!samePositionAsStart) {
            this.options.wysiwyg.odooEditor.historyStep();
        }
        delete this.$dropZones;
        delete this.dragState;
    },
    /**
     * @private
     */
    _onOptionsSectionMouseEnter: function (ev) {
        if (!this.$target.is(':visible')) {
            return;
        }
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
        this.removeSnippet();
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
                ev.stopPropagation();
                ev.data.onSuccess(widget);
                return;
            }
        }
        if (!ev.data.allowParentOption) {
            ev.stopPropagation();
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
    /**
     * Called when the "send to back" overlay button is clicked.
     *
     * @private
     * @param {Event} ev
     */
    _onSendBackClick(ev) {
        ev.stopPropagation();
        const rowEl = this.$target[0].parentNode;
        const columnEls = [...rowEl.children].filter(el => el !== this.$target[0]);
        const minZindex = Math.min(...columnEls.map(el => el.style.zIndex));

        // While the minimum z-index is not 0, it is OK to decrease it and to
        // set the column to it. Otherwise, the column is set to 0 and the
        // other columns z-index are increased by one.
        if (minZindex > 0) {
            this.$target[0].style.zIndex = minZindex - 1;
        } else {
            for (const columnEl of columnEls) {
                columnEl.style.zIndex++;
            }
            this.$target[0].style.zIndex = 0;
        }
    },
    /**
     * Called when the "bring to front" overlay button is clicked.
     *
     * @private
     * @param {Event} ev
     */
    _onBringFrontClick(ev) {
        ev.stopPropagation();
        const rowEl = this.$target[0].parentNode;
        gridUtils._setElementToMaxZindex(this.$target[0], rowEl);
    },
    /**
     * Called when the mouse is moved to place a column in a grid.
     *
     * @private
     * @param {Event} ev
     */
    _onDragMove(ev) {
        const columnEl = this.$target[0];
        const rowEl = columnEl.parentNode;

        // Computing the rowEl position.
        const rowElTop = rowEl.getBoundingClientRect().top + document.documentElement.scrollTop;
        const rowElLeft = rowEl.getBoundingClientRect().left;

        // Getting the column dimensions.
        const borderWidth = parseFloat(window.getComputedStyle(columnEl).borderWidth);
        const columnHeight = columnEl.clientHeight + 2 * borderWidth;
        const columnWidth = columnEl.clientWidth + 2 * borderWidth;
        const columnMiddle = columnWidth / 2;

        // Placing the column where the mouse is.
        const top = ev.pageY - rowElTop;
        const bottom = top + columnHeight;
        let left = ev.pageX - rowElLeft - columnMiddle;

        // Horizontal overflow.
        left = confine(left, 0, rowEl.clientWidth - columnWidth);

        columnEl.style.top = top + 'px';
        columnEl.style.left = left + 'px';

        // Computing the drag helper corresponding grid area.
        const gridProp = gridUtils._getGridProperties(rowEl);

        const rowStart = Math.round(top / (gridProp.rowSize + gridProp.rowGap)) + 1;
        const columnStart = Math.round(left / (gridProp.columnSize + gridProp.columnGap)) + 1;
        const rowEnd = rowStart + this.dragState.columnRowCount;
        const columnEnd = columnStart + this.dragState.columnColCount;

        const dragHelperEl = this.dragState.dragHelperEl;
        if (parseInt(dragHelperEl.style.gridRowStart) !== rowStart) {
            dragHelperEl.style.gridRowStart = rowStart;
            dragHelperEl.style.gridRowEnd = rowEnd;
        }

        if (parseInt(dragHelperEl.style.gridColumnStart) !== columnStart) {
            dragHelperEl.style.gridColumnStart = columnStart;
            dragHelperEl.style.gridColumnEnd = columnEnd;
        }

        // Vertical overflow/underflow.
        // Updating the reference heights, the dropzone and the background grid.
        const startingHeight = this.dragState.startingHeight;
        const currentHeight = this.dragState.currentHeight;
        const backgroundGridEl = this.dragState.backgroundGridEl;
        const dropzoneEl = this.dragState.dropzoneEl;
        const rowOverflow = Math.round((bottom - currentHeight) / (gridProp.rowSize + gridProp.rowGap));
        const updateRows = bottom > currentHeight || bottom <= currentHeight && bottom > startingHeight;
        if (Math.abs(rowOverflow) >= 1 && updateRows) {
            const dropzoneEnd = parseInt(dropzoneEl.style.gridRowEnd);
            dropzoneEl.style.gridRowEnd = dropzoneEnd + rowOverflow;
            backgroundGridEl.style.gridRowEnd = dropzoneEnd + rowOverflow;
            this.dragState.currentHeight += rowOverflow * (gridProp.rowSize + gridProp.rowGap);
        }
    }
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
        'click .o_we_customize_snippet_btn': '_onOptionsTabClick',
        'click .o_we_invisible_entry': '_onInvisibleEntryClick',
        'click #snippet_custom .o_rename_btn': '_onRenameBtnClick',
        'click #snippet_custom .o_delete_btn': '_onDeleteBtnClick',
        'mousedown': '_onMouseDown',
        'input .o_snippet_search_filter_input': '_onSnippetSearchInput',
        'click .o_snippet_search_filter_reset': '_onSnippetSearchResetClick',
        'click .o_we_website_top_actions button[data-action=save]': '_onSaveRequest',
        'click .o_we_website_top_actions button[data-action=cancel]': '_onDiscardClick',
        'click .o_we_website_top_actions button[data-action=mobile]': '_onMobilePreviewClick',
        'click .o_we_website_top_actions button[data-action=undo]': '_onUndo',
        'click .o_we_website_top_actions button[data-action=redo]': '_onRedo',
    },
    custom_events: {
        'activate_insertion_zones': '_onActivateInsertionZones',
        'activate_snippet': '_onActivateSnippet',
        'call_for_each_child_snippet': '_onCallForEachChildSnippet',
        'clone_snippet': '_onCloneSnippet',
        'cover_update': '_onOverlaysCoverUpdate',
        'deactivate_snippet': '_onDeactivateSnippet',
        'drag_and_drop_stop': '_onSnippetDragAndDropStop',
        'drag_and_drop_start': '_onSnippetDragAndDropStart',
        'get_snippet_versions': '_onGetSnippetVersions',
        'find_snippet_template': '_onFindSnippetTemplate',
        'remove_snippet': '_onRemoveSnippet',
        'snippet_edition_request': '_onSnippetEditionRequest',
        'snippet_editor_destroyed': '_onSnippetEditorDestroyed',
        'snippet_removed': '_onSnippetRemoved',
        'snippet_cloned': '_onSnippetCloned',
        'snippet_option_update': '_onSnippetOptionUpdate',
        'snippet_option_visibility_update': '_onSnippetOptionVisibilityUpdate',
        'snippet_thumbnail_url_request': '_onSnippetThumbnailURLRequest',
        'reload_snippet_dropzones': '_disableUndroppableSnippets',
        'request_save': '_onSaveRequest',
        'hide_overlay': '_onHideOverlay',
        'block_preview_overlays': '_onBlockPreviewOverlays',
        'unblock_preview_overlays': '_onUnblockPreviewOverlays',
        'user_value_widget_opening': '_onUserValueWidgetOpening',
        'user_value_widget_closing': '_onUserValueWidgetClosing',
        'reload_snippet_template': '_onReloadSnippetTemplate',
        'request_editable': '_onRequestEditable',
        'disable_loading_effect': '_onDisableLoadingEffect',
        'enable_loading_effect': '_onEnableLoadingEffect',
    },
    // enum of the SnippetsMenu's tabs.
    tabs: {
        BLOCKS: 'blocks',
        OPTIONS: 'options',
        CUSTOM: 'custom',
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
        this.$body = $((options.document || document).body);

        this.options = options;
        if (!this.options.snippets) {
            this.options.snippets = 'web_editor.snippets';
        }
        this.snippetEditors = [];
        this._enabledEditorHierarchy = [];

        this._mutex = new concurrency.Mutex();

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
            '.modal .btn-close',
            '.o_we_crop_widget',
            '.transfo-container',
        ].join(', ');

        this.loadingTimers = {};
        this.loadingElements = {};
        this._loadingEffectDisabled = false;
        this._onClick = this._onClick.bind(this);
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
        // In an iframe, we need to make sure the element is using jquery on its
        // own window and not on the top window lest jquery behave unexpectedly.
        this.$el = this.window.$(this.$el);
        this.$el.data('snippetMenu', this);

        this.customizePanel = document.createElement('div');
        this.customizePanel.classList.add('o_we_customize_panel', 'd-none');
        this._addToolbar();
        this._checkEditorToolbarVisibilityCallback = this._checkEditorToolbarVisibility.bind(this);
        $(this.options.wysiwyg.odooEditor.document.body).on('click', this._checkEditorToolbarVisibilityCallback);

        if (this.options.enableTranslation) {
            // Load the sidebar with the style tab only.
            await this._loadSnippetsTemplates();
            this.$el.find('.o_we_website_top_actions').removeClass('d-none');
            this.$('.o_snippet_search_filter').addClass('d-none');
            this.$('#o_scroll').addClass('d-none');
            this.$('button[data-action="mobilePreview"]').addClass('d-none');
            this.$('#snippets_menu button').removeClass('active').prop('disabled', true);
            this.$('.o_we_customize_snippet_btn').addClass('active').prop('disabled', false);
            this.$('o_we_ui_loading').addClass('d-none');
            $(this.customizePanel).removeClass('d-none');
            this.$('#o_we_editor_toolbar_container').hide();
            this.$('#o-we-editor-table-container').addClass('d-none');
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

        this.emptyOptionsTabContent = document.createElement('div');
        this.emptyOptionsTabContent.classList.add('text-center', 'pt-5');
        this.emptyOptionsTabContent.append(_t("Select a block on your page to style it."));
        this.options.getScrollOptions = this._getScrollOptions.bind(this);

        // Fetch snippet templates and compute it
        defs.push((async () => {
            await this._loadSnippetsTemplates(this.options.invalidateSnippetCache);
            await this._updateInvisibleDOM();
        })());

        // Prepare snippets editor environment
        this.$snippetEditorArea = $('<div/>', {
            id: 'oe_manipulators',
        }).insertAfter(this.$el);

        // Active snippet editor on click in the page
        this.$document.on('click.snippets_menu', '*', this._onClick);
        // Needed as bootstrap stop the propagation of click events for dropdowns
        this.$document.on('mouseup.snippets_menu', '.dropdown-toggle', this._onClick);

        core.bus.on('deactivate_snippet', this, this._onDeactivateSnippet);

        // Adapt overlay covering when the window is resized / content changes
        var debouncedCoverUpdate = _.throttle(() => {
            this.updateCurrentSnippetEditorOverlay();
        }, 50);
        this.$window.on('resize.snippets_menu', debouncedCoverUpdate);
        this.$body.on('content_changed.snippets_menu', debouncedCoverUpdate);
        $(this.$body[0].ownerDocument.defaultView).on('resize.snippets_menu', debouncedCoverUpdate);

        // On keydown add a class on the active overlay to hide it and show it
        // again when the mouse moves
        this.$body.on('keydown.snippets_menu', () => {
            this.__overlayKeyWasDown = true;
            this.snippetEditors.forEach(editor => {
                editor.toggleOverlayVisibility(false);
            });
        });
        this.$body.on('mousemove.snippets_menu, mousedown.snippets_menu', _.throttle(() => {
            if (!this.__overlayKeyWasDown) {
                return;
            }
            this.__overlayKeyWasDown = false;
            this.snippetEditors.forEach(editor => {
                editor.toggleOverlayVisibility(true);
                editor.cover();
            });
        }, 250));

        // Hide the active overlay when scrolling.
        // Show it again and recompute all the overlays after the scroll.
        this.$scrollingElement = $().getScrollingElement(this.$body[0].ownerDocument);
        if (!this.$scrollingElement[0]) {
            this.$scrollingElement = $(this.ownerDocument).find('.o_editable');
        }
        this._onScrollingElementScroll = _.throttle(() => {
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
        }, 50);
        // We use addEventListener instead of jQuery because we need 'capture'.
        // Setting capture to true allows to take advantage of event bubbling
        // for events that otherwise don’t support it. (e.g. useful when
        // scrolling a modal)
        this.$scrollingElement[0].addEventListener('scroll', this._onScrollingElementScroll, {capture: true});

        // Auto-selects text elements with a specific class and remove this
        // on text changes
        this.$body.on('click.snippets_menu', '.o_default_snippet_text', function (ev) {
            $(ev.target).closest('.o_default_snippet_text').removeClass('o_default_snippet_text');
            $(ev.target).selectContent();
            $(ev.target).removeClass('o_default_snippet_text');
        });
        this.$body.on('keyup.snippets_menu', function () {
            const selection = this.ownerDocument.getSelection();
            if (!Selection.rangeCount) {
                return;
            }
            const range = selection.getRangeAt(0);
            $(range.startContainer).closest('.o_default_snippet_text').removeClass('o_default_snippet_text');
        });
        const refreshSnippetEditors = _.debounce(() => {
            for (const snippetEditor of this.snippetEditors) {
                this._mutex.exec(() => snippetEditor.destroy());
            }
            // FIXME should not the snippetEditors list be emptied here ?
            const selection = this.$body[0].ownerDocument.getSelection();
            if (selection.rangeCount) {
                const target = selection.getRangeAt(0).startContainer.parentElement;
                this._activateSnippet($(target));
            }

            this._updateInvisibleDOM();
        }, 500);
        this.options.wysiwyg.odooEditor.addEventListener('historyUndo', refreshSnippetEditors);
        this.options.wysiwyg.odooEditor.addEventListener('historyRedo', refreshSnippetEditors);

        const $autoFocusEls = $('.o_we_snippet_autofocus');
        this._activateSnippet($autoFocusEls.length ? $autoFocusEls.first() : false);

        // Add tooltips on we-title elements whose text overflows
        this.$el.tooltip({
            selector: 'we-title',
            placement: 'bottom',
            delay: 100,
            title: function () {
                const el = this;
                if (el.tagName !== 'WE-TITLE') {
                    return el.title;
                }
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
            const $undoButton = this.$('.o_we_external_history_buttons button[data-action="undo"]');
            const $redoButton = this.$('.o_we_external_history_buttons button[data-action="redo"]');
            if ($undoButton.length) {
                const updateHistoryButtons = () => {
                    $undoButton.attr('disabled', !this.options.wysiwyg.odooEditor.historyCanUndo());
                    $redoButton.attr('disabled', !this.options.wysiwyg.odooEditor.historyCanRedo());
                };
                this.options.wysiwyg.odooEditor.addEventListener('historyStep', updateHistoryButtons);
                this.options.wysiwyg.odooEditor.addEventListener('observerApply', () => {
                    $(this.options.wysiwyg.odooEditor.editable).trigger('content_changed');
                });
                this.options.wysiwyg.odooEditor.addEventListener('historyRevert', _.debounce(() => {
                    this.trigger_up('widgets_start_request', {
                        $target: this.options.wysiwyg.$editable,
                        editableMode: true,
                    });
                }, 50));
            }

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
            if (this.$snippetEditorArea) {
                this.$snippetEditorArea.remove();
            }
            this.$window.off('.snippets_menu');
            this.$document.off('.snippets_menu');
            if (this.$scrollingElement) {
                this.$scrollingElement[0].removeEventListener('scroll', this._onScrollingElementScroll, {capture: true});
            }
        }
        core.bus.off('deactivate_snippet', this, this._onDeactivateSnippet);
        $(document.body).off('click', this._checkEditorToolbarVisibilityCallback);
        this.el.ownerDocument.body.classList.remove('editor_has_snippets');
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
        // First disable the snippet selection, calling options onBlur, closing
        // widgets, etc. Then wait for full resolution of the mutex as widgets
        // may have triggered some final edition requests that need to be
        // processed before actual "clean for save" and saving.
        await this._activateSnippet(false);
        await this._mutex.getUnlockedDef();

        // Next, notify that we want the DOM to be cleaned (e.g. in website this
        // may be the moment where the public widgets need to be destroyed).
        this.trigger_up('ready_to_clean_for_save');
        // Wait for the mutex a second time as some options do editor actions when
        // their snippets are destroyed. (E.g. s_popup triggers visibility updates
        // when hidden, destroying the widget hides it.)
        await this._mutex.getUnlockedDef();

        // Then destroy all snippet editors, making them call their own
        // "clean for save" methods (and options ones).
        await this._destroyEditors();

        // Final editor cleanup
        this.getEditableArea().find('[contentEditable]')
            .removeAttr('contentEditable')
            .removeProp('contentEditable');
        this.getEditableArea().find('.o_we_selected_image')
            .removeClass('o_we_selected_image');
    },
    /**
     * Load snippets.
     * @param {boolean} invalidateCache
     */
    loadSnippets: function (invalidateCache) {
        if (!invalidateCache && cacheSnippetTemplate[this.options.snippets]) {
            this._defLoadSnippets = cacheSnippetTemplate[this.options.snippets];
            return this._defLoadSnippets;
        }
        this._defLoadSnippets = this._rpc({
            model: 'ir.ui.view',
            method: 'render_public_asset',
            args: [this.options.snippets, {}],
            kwargs: {
                context: this.options.context,
            },
        }, { shadow: true });
        cacheSnippetTemplate[this.options.snippets] = this._defLoadSnippets;
        return this._defLoadSnippets;
    },
    /**
     * Get the editable area.
     *
     * @returns {JQuery}
     */
    getEditableArea: function () {
        return this.options.wysiwyg.$editable.find(this.options.selectorEditableArea)
            .add(this.options.wysiwyg.$editable.filter(this.options.selectorEditableArea));
    },
    /**
     * Updates the cover dimensions of the current snippet editor.
     */
    updateCurrentSnippetEditorOverlay: function () {
        if (this.snippetEditorDragging) {
            return;
        }
        for (const snippetEditor of this.snippetEditors) {
            if (snippetEditor.$target.closest('body').length) {
                snippetEditor.cover();
                continue;
            }
            // Destroy options whose $target are not in the DOM anymore but
            // only do it once all options executions are done.
            this._mutex.exec(() => this._destroyEditor(snippetEditor));
        }
        this._mutex.exec(() => {
            if (this._currentTab === this.tabs.OPTIONS && !this.snippetEditors.length) {
                this._activateEmptyOptionsTab();
            }
        });
    },
    activateCustomTab: function (content) {
        this._updateRightPanelContent({content: content, tab: this.tabs.CUSTOM});
    },
    /**
     * Public method to activate a snippet.
     *
     * @see this._activateSnippet
     * @param {jQuery} $snippet
     * @returns {Promise}
     */
    activateSnippet: async function ($snippet) {
        return this._activateSnippet($snippet);
    },

    /**
     * Postprocesses a snippet node when it has been inserted in the dom.
     *
     * @param {jQuery} $target
     * @returns {Promise}
     */
    callPostSnippetDrop: async function ($target) {
        // First call the onBuilt of all options of each item in the snippet
        // (and so build their editor instance first).
        await this._callForEachChildSnippet($target, function (editor, $snippet) {
            return editor.buildSnippet();
        });
        // The snippet is now fully built, notify the editor for changed
        // content.
        $target.trigger('content_changed');

        // Now notifies that a snippet was dropped (at the moment, useful to
        // start public widgets for instance (no saved content)).
        await this._mutex.exec(() => {
            const proms = [];
            this.trigger_up('snippet_dropped', {
                $target: $target,
                addPostDropAsync: prom => proms.push(prom),
            });
            return Promise.all(proms);
        });

        // Lastly, ensure that the snippets or its related parts are added to
        // the invisible DOM list if needed.
        await this._updateInvisibleDOM();
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
     * @param {string or boolean} canBeSanitizedUnless
     *        true: always allows,
     *        false: always forbid,
     *        string: specific type of forbidden sanitization
     * @param {Object} [selectorGrids = []]
     *        elements which are in grid mode and for which a grid dropzone
     *        needs to be inserted
     */
    _activateInsertionZones($selectorSiblings, $selectorChildren, canBeSanitizedUnless, selectorGrids = []) {
        var self = this;

        // If a modal or a dropdown is open, the drop zones must be created
        // only in this element.
        const $editableArea = self.getEditableArea();
        let $open = $editableArea.find('.modal:visible');
        if (!$open.length) {
            $open = $editableArea.find('.dropdown-menu.show').addBack('.dropdown-menu.show').parent();
        }
        if ($open.length) {
            $selectorSiblings = $open.find($selectorSiblings);
            $selectorChildren = $open.find($selectorChildren);
        }

        // Check if the drop zone should be horizontal or vertical
        function setDropZoneDirection($elem, $parent, $sibling) {
            var vertical = false;
            var style = {};
            $sibling = $sibling || $elem;
            var css = window.getComputedStyle($elem[0]);
            var parentCss = window.getComputedStyle($parent[0]);
            var float = css.float || css.cssFloat;
            var display = parentCss.display;
            var flex = parentCss.flexDirection;
            if (float === 'left' || float === 'right' || (display === 'flex' && flex === 'row')) {
                style['float'] = float;
                if ($sibling.parent().width() !== $sibling.outerWidth(true)) {
                    vertical = true;
                    style['height'] = Math.max($sibling.outerHeight(), 30) + 'px';
                }
            }
            return {
                vertical: vertical,
                style: style,
            };
        }

        // If the previous sibling is a BR tag or a non-whitespace text, it
        // should be a vertical dropzone.
        function testPreviousSibling(node, $zone) {
            if (!node || ((node.tagName || !node.textContent.match(/\S/)) && node.tagName !== 'BR')) {
                return false;
            }
            return {
                vertical: true,
                style: {
                    'float': 'none',
                    'display': 'inline-block',
                    'height': parseInt(self.window.getComputedStyle($zone[0]).lineHeight) + 'px',
                },
            };
        }

        // Firstly, add a dropzone after the clone (if we are not in grid mode).
        var $clone = this.$body.find('.oe_drop_clone');
        if ($clone.length && $clone.closest('div.o_grid_mode').length === 0) {
            var $neighbor = $clone.prev();
            if (!$neighbor.length) {
                $neighbor = $clone.next();
            }
            var data;
            if ($neighbor.length) {
                data = setDropZoneDirection($neighbor, $neighbor.parent());
            } else {
                data = {
                    vertical: false,
                    style: {},
                };
            }
            self._insertDropzone($('<we-hook/>').insertAfter($clone), data.vertical, data.style, canBeSanitizedUnless);
        }

        if ($selectorChildren) {
            $selectorChildren.each(function () {
                var data;
                var $zone = $(this);
                var $children = $zone.find('> :not(.oe_drop_zone, .oe_drop_clone)');

                if (!$zone.children().last().is('.oe_drop_zone')) {
                    data = testPreviousSibling($zone[0].lastChild, $zone)
                        || setDropZoneDirection($zone, $zone, $children.last());
                    self._insertDropzone($('<we-hook/>').appendTo($zone), data.vertical, data.style, canBeSanitizedUnless);
                }

                if (!$zone.children().first().is('.oe_drop_clone')) {
                    data = testPreviousSibling($zone[0].firstChild, $zone)
                        || setDropZoneDirection($zone, $zone, $children.first());
                    self._insertDropzone($('<we-hook/>').prependTo($zone), data.vertical, data.style, canBeSanitizedUnless);
                }
            });

            // add children near drop zone
            $selectorSiblings = $(_.uniq(($selectorSiblings || $()).add($selectorChildren.children()).get()));
        }

        var noDropZonesSelector = '[data-invisible="1"], .o_we_no_overlay, :not(:visible)';
        if ($selectorSiblings) {
            $selectorSiblings.not(`.oe_drop_zone, .oe_drop_clone, ${noDropZonesSelector}`).each(function () {
                var data;
                var $zone = $(this);
                var $zoneToCheck = $zone;

                while ($zoneToCheck.prev(noDropZonesSelector).length) {
                    $zoneToCheck = $zoneToCheck.prev();
                }
                if (!$zoneToCheck.prev('.oe_drop_zone:visible, .oe_drop_clone').length) {
                    data = setDropZoneDirection($zone, $zone.parent());
                    self._insertDropzone($('<we-hook/>').insertBefore($zone), data.vertical, data.style, canBeSanitizedUnless);
                }

                $zoneToCheck = $zone;
                while ($zoneToCheck.next(noDropZonesSelector).length) {
                    $zoneToCheck = $zoneToCheck.next();
                }
                if (!$zoneToCheck.next('.oe_drop_zone:visible, .oe_drop_clone').length) {
                    data = setDropZoneDirection($zone, $zone.parent());
                    self._insertDropzone($('<we-hook/>').insertAfter($zone), data.vertical, data.style, canBeSanitizedUnless);
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

        let iframeOffset;
        const bodyWindow = this.$body[0].ownerDocument.defaultView;
        if (bodyWindow.frameElement && bodyWindow !== this.ownerDocument.defaultView) {
            iframeOffset = bodyWindow.frameElement.getBoundingClientRect();
        }

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

            // In the case of the SnippetsMenu being instanciated in the global
            // document, with its editable content in an iframe, we want to
            // take the iframe's offset into account to compute the dropzones.
            if (iframeOffset) {
                this.oldGetBoundingClientRect = this.getBoundingClientRect;
                this.getBoundingClientRect = () => {
                    const rect = this.oldGetBoundingClientRect();
                    const { x, y } = iframeOffset;
                    rect.x += x;
                    rect.y += y;
                    return rect;
                };
            }
        });

        // Inserting a grid dropzone for each row in grid mode.
        for (const rowEl of selectorGrids) {
            self._insertGridDropzone(rowEl);
        }
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
            this.options.wysiwyg.odooEditor.automaticStepSkipStack();
            this.invisibleDOMMap = new Map();
            const $invisibleDOMPanelEl = $(this.invisibleDOMPanelEl);
            $invisibleDOMPanelEl.find('.o_we_invisible_entry').remove();
            const $invisibleSnippets = globalSelector.all().find('.o_snippet_invisible').addBack('.o_snippet_invisible');

            $invisibleDOMPanelEl.toggleClass('d-none', !$invisibleSnippets.length);

            const proms = _.map($invisibleSnippets, async el => {
                const editor = await this._createSnippetEditor($(el));
                const $invisEntry = $('<div/>', {
                    class: 'o_we_invisible_entry d-flex align-items-center justify-content-between',
                    text: editor.getName(),
                }).append($('<i/>', {class: `fa ${editor.isTargetVisible() ? 'fa-eye' : 'fa-eye-slash'} ms-2`}));
                $invisibleDOMPanelEl.append($invisEntry);
                this.invisibleDOMMap.set($invisEntry[0], el);
            });
            return Promise.all(proms);
        }, false);
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
    _activateSnippet: async function ($snippet, previewMode, ifInactiveOptions) {
        if (this._blockPreviewOverlays && previewMode) {
            return;
        }
        if ($snippet && !$snippet.is(':visible')) {
            return;
        }
        // Take the first parent of the provided DOM (or itself) which
        // should have an associated snippet editor.
        // It is important to do that before the mutex exec call to compute it
        // before potential ancestor removal.
        if ($snippet && $snippet.length) {
            const $globalSnippet = globalSelector.closest($snippet);
            if (!$globalSnippet.length) {
                $snippet = $snippet.closest('[data-oe-model="ir.ui.view"]:not([data-oe-type]):not(.oe_structure), [data-oe-type="html"]:not(.oe_structure)');
            } else {
                $snippet = $globalSnippet;
            }
        }
        const exec = previewMode
            ? action => this._mutex.exec(action)
            : action => this._execWithLoadingEffect(action, false);
        return exec(() => {
            return new Promise(resolve => {
                if ($snippet && $snippet.length) {
                    return this._createSnippetEditor($snippet).then(resolve);
                }
                resolve(null);
            }).then(async editorToEnable => {
                if (!previewMode && this._enabledEditorHierarchy[0] === editorToEnable
                        || ifInactiveOptions && this._enabledEditorHierarchy.includes(editorToEnable)) {
                    return editorToEnable;
                }

                if (!previewMode) {
                    this._enabledEditorHierarchy = [];
                    let current = editorToEnable;
                    while (current && current.$target) {
                        this._enabledEditorHierarchy.push(current);
                        current = current.getParent();
                    }
                }

                // First disable all editors...
                for (let i = this.snippetEditors.length; i--;) {
                    const editor = this.snippetEditors[i];
                    editor.toggleOverlay(false, previewMode);
                    if (!previewMode) {
                        const wasShown = !!await editor.toggleOptions(false);
                        if (wasShown) {
                            this._updateRightPanelContent({
                                content: [],
                                tab: this.tabs.BLOCKS,
                            });
                        }
                    }
                }
                // ... then enable the right editor or look if some have been
                // enabled previously by a click
                let customize$Elements;
                if (editorToEnable) {
                    editorToEnable.toggleOverlay(true, previewMode);
                    if (!previewMode && !editorToEnable.displayOverlayOptions) {
                        const parentEditor = this._enabledEditorHierarchy.find(ed => ed.displayOverlayOptions);
                        if (parentEditor) {
                            parentEditor.toggleOverlay(true, previewMode);
                        }
                    }
                    customize$Elements = await editorToEnable.toggleOptions(true);
                } else {
                    for (const editor of this.snippetEditors) {
                        if (editor.isSticky()) {
                            editor.toggleOverlay(true, false);
                            customize$Elements = await editor.toggleOptions(true);
                            break;
                        }
                    }
                }

                if (!previewMode) {
                    this._updateRightPanelContent({
                        content: customize$Elements || [],
                        tab: customize$Elements ? this.tabs.OPTIONS : this.tabs.BLOCKS,
                    });
                }

                return editorToEnable;
            }).then(editor => {
                // If a link was clicked, the linktools should be focused after
                // the right panel is shown to the user.
                if (this._currentTab === this.tabs.OPTIONS
                        && this.options.wysiwyg.linkTools
                        && !this.options.wysiwyg.linkTools.noFocusUrl) {
                    this.options.wysiwyg.linkTools.focusUrl();
                }
                return editor;
            });
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
     * TODO everything related to SnippetEditor destroy / cleanForSave should
     * really be cleaned / unified.
     *
     * @private
     * @param {SnippetEditor} editor
     */
    _destroyEditor(editor) {
        editor.destroy();
        const index = this.snippetEditors.indexOf(editor);
        if (index >= 0) {
            this.snippetEditors.splice(index, 1);
        }
    },
    /**
     * @private
     * @param {jQuery|null|undefined} [$el]
     *        The DOM element whose inside editors need to be destroyed.
     *        If no element is given, all the editors are destroyed.
     */
    _destroyEditors: async function ($el) {
        const aliveEditors = this.snippetEditors.filter((snippetEditor) => {
            return !$el || $el.has(snippetEditor.$target).length;
        });
        const cleanForSavePromises = aliveEditors.map((snippetEditor) => snippetEditor.cleanForSave());
        await Promise.all(cleanForSavePromises);

        for (const snippetEditor of aliveEditors) {
            // No need to clean the `this.snippetEditors` array as each
            // individual destroy notifies this class instance to remove the
            // element from the array.
            snippetEditor.destroy();
        }
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
     * @param {string} excludeParent
     *        jQuery selector that the parents of DOM elements must *not* match
     *        to be considered as potential snippet.
     */
    _computeSelectorFunctions: function (selector, exclude, target, noCheck, isChildren, excludeParent) {
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
        if (excludeParent) {
            const oldFilter = filterFunc;
            filterFunc = function () {
                return oldFilter.apply(this) && !$(this).parent().is(excludeParent);
            };
        }

        // Prepare the functions
        const functions = {};
        if (noCheck) {
            functions.is = function ($from) {
                return $from.is(selector) && $from.filter(filterFunc).length !== 0;
            };
            functions.closest = function ($from, parentNode) {
                return $from.closest(selector, parentNode).filter(filterFunc);
            };
            functions.all = function ($from) {
                return ($from ? dom.cssFind($from, selector) : self.$body.find(selector)).filter(filterFunc);
            };
        } else {
            functions.is = function ($from) {
                return $from.is(selector)
                    && self.getEditableArea().find($from).addBack($from).length !== 0
                    && $from.filter(filterFunc).length !== 0;
            };
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
                }).filter(filterFunc);
            };
            functions.all = isChildren ? function ($from) {
                return dom.cssFind($from || self.getEditableArea(), selector).filter(filterFunc);
            } : function ($from) {
                $from = $from || self.getEditableArea();
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
    _computeSnippetTemplates: function (html) {
        var self = this;
        var $html = $(html);
        var $scroll = $html.siblings('#o_scroll');

        this.templateOptions = [];
        var selectors = [];
        var $styles = $html.find('[data-selector]');
        const snippetAdditionDropIn = $styles.filter('#so_snippet_addition').data('drop-in');
        $styles.each(function () {
            var $style = $(this);
            var selector = $style.data('selector');
            var exclude = $style.data('exclude') || '';
            const excludeParent = $style.attr('id') === "so_content_addition" ? snippetAdditionDropIn : '';
            var target = $style.data('target');
            var noCheck = $style.data('no-check');
            var optionID = $style.data('js') || $style.data('option-name'); // used in tour js as selector
            var option = {
                'option': optionID,
                'base_selector': selector,
                'base_exclude': exclude,
                'base_target': target,
                'selector': self._computeSelectorFunctions(selector, exclude, target, noCheck),
                '$el': $style,
                'drop-near': $style.data('drop-near') && self._computeSelectorFunctions($style.data('drop-near'), '', false, noCheck, true, excludeParent),
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
            .each((i, el) => {
                const $snippet = $(el);
                const name = _.escape(el.getAttribute('name'));
                const thumbnailSrc = _.escape(el.dataset.oeThumbnail);
                const $sbody = $snippet.children().addClass('oe_snippet_body');
                const isCustomSnippet = !!el.closest('#snippet_custom');

                // Associate in-page snippets to their name
                // TODO I am not sure this is useful anymore and it should at
                // least be made more robust using data-snippet
                let snippetClasses = $sbody.attr('class').match(/s_[^ ]+/g);
                if (snippetClasses && snippetClasses.length) {
                    snippetClasses = '.' + snippetClasses.join('.');
                }
                const $els = self.$body.find(snippetClasses).not('[data-name]').add($(snippetClasses)).add($sbody);
                $els.attr('data-name', name).data('name', name);

                // Create the thumbnail
                const $thumbnail = $(`
                    <div class="oe_snippet_thumbnail">
                        <div class="oe_snippet_thumbnail_img" style="background-image: url(${thumbnailSrc});"/>
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

                // Create the rename and delete button for custom snippets
                if (isCustomSnippet) {
                    const btnRenameEl = document.createElement('we-button');
                    btnRenameEl.dataset.snippetId = $snippet.data('oeSnippetId');
                    btnRenameEl.classList.add('o_rename_btn', 'fa', 'fa-pencil', 'btn', 'o_we_hover_success');
                    btnRenameEl.title = _.str.sprintf(_t("Rename %s"), name);
                    $snippet.append(btnRenameEl);
                    const btnEl = document.createElement('we-button');
                    btnEl.dataset.snippetId = $snippet.data('oeSnippetId');
                    btnEl.classList.add('o_delete_btn', 'fa', 'fa-trash', 'btn', 'o_we_hover_danger');
                    btnEl.title = _.str.sprintf(_t("Delete %s"), name);
                    $snippet.append(btnEl);
                }
            })
            .not('[data-module-id]');

        // Enable the snippet tooltips
        this.$snippets.tooltip({
            trigger: 'manual',
            placement: 'bottom',
            title: _t("Drag and drop the building block."),
        });

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
        this.$el.append(this.invisibleDOMPanelEl);
        this._makeSnippetDraggable(this.$snippets);
        this._disableUndroppableSnippets();

        this.$el.addClass('o_loaded');
        $(this.el.ownerDocument.body).addClass('editor_has_snippets');
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
        if (!$snippet[0].classList.contains('o_no_parent_editor')) {
            var $parent = globalSelector.closest($snippet.parent());
            if ($parent.length) {
                def = this._createSnippetEditor($parent);
            }
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
            // Keep parent below its child inside the DOM as its `o_handle`
            // needs to be (visually) on top of the child ones.
            return snippetEditor.prependTo(self.$snippetEditorArea);
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
            const isSanitizeForbidden = $snippet.data('oeForbidSanitize');
            const filterSanitize = isSanitizeForbidden === 'form'
                ? $els => $els.filter((i, el) => !el.closest('[data-oe-sanitize]:not([data-oe-sanitize="allow_form"])'))
                : isSanitizeForbidden
                    ? $els => $els.filter((i, el) => !el.closest('[data-oe-sanitize]'))
                    : $els => $els;

            var check = false;
            _.each(self.templateOptions, function (option, k) {
                if (check || !($snippetBody.is(option.base_selector) && !$snippetBody.is(option.base_exclude))) {
                    return;
                }

                k = isSanitizeForbidden ? 'forbidden/' + k : k;
                cache[k] = cache[k] || {
                    'drop-near': option['drop-near'] ? filterSanitize(option['drop-near'].all()).length : 0,
                    'drop-in': option['drop-in'] ? filterSanitize(option['drop-in'].all()).length : 0,
                };
                check = (cache[k]['drop-near'] || cache[k]['drop-in']);
            });

            $snippet.toggleClass('o_disabled', !check);
            $snippet.attr('title', check ? '' : _t("No location to drop in"));
            const $icon = $snippet.find('.o_snippet_undroppable').remove();
            if (check) {
                $icon.remove();
            } else if (!$icon.length) {
                const imgEl = document.createElement('img');
                imgEl.classList.add('o_snippet_undroppable');
                imgEl.src = '/web_editor/static/src/img/snippet_disabled.svg';
                $snippet.append(imgEl);
            }
        });
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
                appendTo: this.$body,
                cursor: 'move',
                greedy: true,
                scroll: false,
            }, options.jQueryDraggableOptions),
            disableHorizontalScroll: true,
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
     * @param {string or boolean} canBeSanitizedUnless
     *    true: always allow
     *    'form': allow if forms are allowed
     *    false: always fobid
     */
    _insertDropzone: function ($hook, vertical, style, canBeSanitizedUnless) {
        let forbidSanitize;
        if (canBeSanitizedUnless === 'form') {
            forbidSanitize = $hook.closest('[data-oe-sanitize]:not([data-oe-sanitize="allow_form"])').length;
        } else {
            forbidSanitize = !canBeSanitizedUnless && $hook.closest('[data-oe-sanitize]').length;
        }
        var $dropzone = $('<div/>', {
            'class': 'oe_drop_zone oe_insert' + (vertical ? ' oe_vertical' : '') +
                (forbidSanitize ? ' text-center oe_drop_zone_danger' : ''),
        });
        if (style) {
            $dropzone.css(style);
        }
        if (forbidSanitize) {
            $dropzone[0].appendChild(document.createTextNode(
                _t("For technical reasons, this block cannot be dropped here")
            ));
        }
        $hook.replaceWith($dropzone);
        return $dropzone;
    },
    /**
     * Creates a dropzone taking the entire area of the row in grid mode in
     * which it will be added. It allows to place elements dragged over it
     * inside the grid it belongs to.
     *
     * @param {Element} rowEl
     */
    _insertGridDropzone(rowEl) {
        const columnCount = 12;
        const rowCount = parseInt(rowEl.dataset.rowCount);
        let $dropzone = $('<div/>', {
            'class': 'oe_drop_zone oe_insert oe_grid_zone',
            'style': 'grid-area: ' + 1 + '/' + 1 + '/' + (rowCount + 1) + '/' + (columnCount + 1),
        });
        $dropzone[0].style.minHeight = window.getComputedStyle(rowEl).height;
        $dropzone[0].style.width = window.getComputedStyle(rowEl).width;
        rowEl.append($dropzone[0]);
    },
    /**
     * Make given snippets be draggable/droppable thanks to their thumbnail.
     *
     * @private
     * @param {jQuery} $snippets
     */
    _makeSnippetDraggable: function ($snippets) {
        var self = this;
        var $toInsert, dropped, $snippet;
        let $dropZones;

        let dragAndDropResolve;
        let $scrollingElement = $().getScrollingElement(this.$body[0].ownerDocument);
        if (!$scrollingElement[0] || $scrollingElement.find('body.o_in_iframe').length) {
            $scrollingElement = $(this.ownerDocument).find('.o_editable');
        }

        const smoothScrollOptions = this._getScrollOptions({
            jQueryDraggableOptions: {
                handle: '.oe_snippet_thumbnail:not(.o_we_already_dragging)',
                helper: function () {
                    const dragSnip = this.cloneNode(true);
                    dragSnip.querySelectorAll('.o_delete_btn, .o_rename_btn').forEach(
                        el => el.remove()
                    );
                    self.$el[0].ownerDocument.body.append(dragSnip);
                    return dragSnip;
                },
                start: function () {
                    self._hideSnippetTooltips();

                    const prom = new Promise(resolve => dragAndDropResolve = () => resolve());
                    self._mutex.exec(() => prom);

                    const doc = self.options.wysiwyg.odooEditor.document;
                    $(doc.body).addClass('oe_dropzone_active');

                    self.options.wysiwyg.odooEditor.automaticStepUnactive();

                    self.$el.find('.oe_snippet_thumbnail').addClass('o_we_already_dragging');
                    self.options.wysiwyg.odooEditor.observerUnactive('dragAndDropCreateSnippet');

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
                    // Color-customize dynamic SVGs in dropped snippets with current theme colors.
                    [...$toInsert.find('img[src^="/web_editor/shape/"]')].forEach(dynamicSvg => {
                        const colorCustomizedURL = new URL(dynamicSvg.getAttribute('src'), window.location.origin);
                        colorCustomizedURL.searchParams.forEach((value, key) => {
                            const match = key.match(/^c([1-5])$/);
                            if (match) {
                                colorCustomizedURL.searchParams.set(key, getCSSVariableValue(`o-color-${match[1]}`));
                            }
                        });
                        dynamicSvg.src = colorCustomizedURL.pathname + colorCustomizedURL.search;
                    });

                    if (!$selectorSiblings.length && !$selectorChildren.length) {
                        console.warn($snippet.find('.oe_snippet_thumbnail_title').text() + " have not insert action: data-drop-near or data-drop-in");
                        return;
                    }

                    const forbidSanitize = $snippet.data('oeForbidSanitize');
                    const canBeSanitizedUnless = forbidSanitize === 'form' ? 'form' : !forbidSanitize;
                    self._activateInsertionZones($selectorSiblings, $selectorChildren, canBeSanitizedUnless);
                    $dropZones = self.getEditableArea().find('.oe_drop_zone');
                    if (forbidSanitize === 'form') {
                        $dropZones = $dropZones.filter((i, el) => !el.closest('[data-oe-sanitize]:not([data-oe-sanitize="allow_form"]) .oe_drop_zone'));
                    } else if (forbidSanitize) {
                        $dropZones = $dropZones.filter((i, el) => !el.closest('[data-oe-sanitize] .oe_drop_zone'));
                    }
                    $dropZones.droppable({
                        over: function () {
                            if (dropped) {
                                $toInsert.detach();
                                $toInsert.addClass('oe_snippet_body');
                                $('.oe_drop_zone').removeClass('invisible');
                            }
                            dropped = true;
                            $(this).first().after($toInsert).addClass('invisible');
                            $toInsert.removeClass('oe_snippet_body');
                            self.trigger_up('drop_zone_over');
                        },
                        out: function () {
                            var prev = $toInsert.prev();
                            if (this === prev[0]) {
                                dropped = false;
                                $toInsert.detach();
                                $(this).removeClass('invisible');
                                $toInsert.addClass('oe_snippet_body');
                            }
                            self.trigger_up('drop_zone_out');
                        },
                    });
                    // If a modal is open, the scroll target must be that modal
                    const $openModal = self.getEditableArea().find('.modal:visible');
                    if ($openModal.length) {
                        self.draggableComponent.$scrollTarget = $openModal;
                    }

                    // Trigger a scroll on the draggable element so that jQuery updates
                    // the position of the drop zones.
                    self.draggableComponent.$scrollTarget.on('scroll.scrolling_element', function () {
                        self.$el.trigger('scroll');
                    });
                    self.trigger_up('drop_zone_start');
                },
                stop: async function (ev, ui) {
                    const doc = self.options.wysiwyg.odooEditor.document;
                    $(doc.body).removeClass('oe_dropzone_active');
                    self.options.wysiwyg.odooEditor.automaticStepUnactive();
                    self.options.wysiwyg.odooEditor.automaticStepSkipStack();
                    $toInsert.removeClass('oe_snippet_body');
                    self.draggableComponent.$scrollTarget.off('scroll.scrolling_element');
                    if (!dropped && ui.position.top > 3 && ui.position.left + ui.helper.outerHeight() < self.el.getBoundingClientRect().left) {
                        const point = {x: ui.position.left, y: ui.position.top};
                        const container = {container: doc.body};
                        let droppedOnNotNearest = doc.defaultView.$.touching(
                            point, '.oe_structure_not_nearest', container
                        ).first();
                        // If dropped outside of a dropzone with class oe_structure_not_nearest,
                        // move the snippet to the nearest dropzone without it
                        const selector = droppedOnNotNearest.length
                            ? '.oe_drop_zone'
                            : ':not(.oe_structure_not_nearest) > .oe_drop_zone';
                        let $el = doc.defaultView.$.nearest(
                            point, selector, container
                        ).first();
                        // Some drop zones might have been disabled.
                        $el = $el.filter($dropZones);
                        if ($el.length) {
                            $el.after($toInsert);
                            dropped = true;
                        }
                    }

                    $dropZones.droppable('destroy');
                    self.getEditableArea().find('.oe_drop_zone').remove();

                    let $toInsertParent;
                    let prev;
                    let next;
                    if (dropped) {
                        prev = $toInsert.first()[0].previousSibling;
                        next = $toInsert.last()[0].nextSibling;

                        $toInsertParent = $toInsert.parent();
                        $toInsert.detach();
                    }

                    self.options.wysiwyg.odooEditor.observerActive('dragAndDropCreateSnippet');

                    if (dropped) {
                        if (prev) {
                            $toInsert.insertAfter(prev);
                        } else if (next) {
                            $toInsert.insertBefore(next);
                        } else {
                            $toInsertParent.prepend($toInsert);
                        }

                        var $target = $toInsert;


                        self.options.wysiwyg.odooEditor.observerUnactive('dragAndDropCreateSnippet');
                        await self._scrollToSnippet($target, self.$scrollable);
                        self.options.wysiwyg.odooEditor.observerActive('dragAndDropCreateSnippet');


                        _.defer(async function () {
                            // Free the mutex now to allow following operations
                            // (mutexed as well).
                            dragAndDropResolve();

                            await self.callPostSnippetDrop($target);

                            // Restore editor to its normal edition state, also
                            // make sure the undroppable snippets are updated.
                            self._disableUndroppableSnippets();
                            self.options.wysiwyg.odooEditor.unbreakableStepUnactive();
                            self.options.wysiwyg.odooEditor.historyStep();
                            self.$el.find('.oe_snippet_thumbnail').removeClass('o_we_already_dragging');
                        });
                    } else {
                        $toInsert.remove();
                        if (dragAndDropResolve) {
                            dragAndDropResolve();
                        }
                        self.$el.find('.oe_snippet_thumbnail').removeClass('o_we_already_dragging');
                    }
                    self.trigger_up('drop_zone_stop');
                },
            },
        });
        this.draggableComponent = new SmoothScrollOnDrag(this, $snippets, $scrollingElement, smoothScrollOptions);
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
     * Changes the content of the left panel and selects a tab.
     *
     * @private
     * @param {htmlString | Element | Text | Array | jQuery} [content]
     * the new content of the customizePanel
     * @param {this.tabs.VALUE} [tab='blocks'] - the tab to select
     */
    _updateRightPanelContent: function ({content, tab, ...options}) {
        this._closeWidgets();

        this._currentTab = tab || this.tabs.BLOCKS;

        this._$toolbarContainer[0].remove();
        if (content) {
            while (this.customizePanel.firstChild) {
                this.customizePanel.removeChild(this.customizePanel.firstChild);
            }
            $(this.customizePanel).append(content);
            if (this._currentTab === this.tabs.OPTIONS && !options.forceEmptyTab) {
                this._addToolbar();
            }
        }

        this.$('.o_snippet_search_filter').toggleClass('d-none', this._currentTab !== this.tabs.BLOCKS);
        this.$('#o_scroll').toggleClass('d-none', this._currentTab !== this.tabs.BLOCKS);
        this.customizePanel.classList.toggle('d-none', this._currentTab === this.tabs.BLOCKS);
        // Remove active class of custom button (e.g. mass mailing theme selection).
        this.$('#snippets_menu button').removeClass('active');
        this.$('.o_we_add_snippet_btn').toggleClass('active', this._currentTab === this.tabs.BLOCKS);
        this.$('.o_we_customize_snippet_btn').toggleClass('active', this._currentTab === this.tabs.OPTIONS);
    },
    /**
     * Scrolls to given snippet.
     *
     * @private
     * @param {jQuery} $el - snippet to scroll to
     * @param {jQuery} [$scrollable] - $element to scroll
     * @return {Promise}
     */
    async _scrollToSnippet($el, $scrollable) {
        // Don't scroll if $el is added to a visible popup that does not fill
        // the page (otherwise the page would scroll to a random location).
        const modalEl = $el[0].closest('.modal');
        if (modalEl && !dom.hasScrollableContent(modalEl)) {
            return;
        }
        return dom.scrollTo($el[0], {extraOffset: 50, $scrollable: $scrollable});
    },
    /**
     * @private
     * @returns {HTMLElement}
     */
    _createLoadingElement() {
        const loaderContainer = document.createElement('div');
        const loader = document.createElement('img');
        const loaderContainerClassList = [
            'o_we_ui_loading',
            'd-flex',
            'justify-content-center',
            'align-items-center',
        ];
        loaderContainer.classList.add(...loaderContainerClassList);
        loader.setAttribute('src', '/web/static/img/spin.svg');
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
            const addLoader = () => {
                if (this._loadingEffectDisabled || this.loadingElements[contentLoading]) {
                    return;
                }
                this.loadingElements[contentLoading] = this._createLoadingElement();
                if (contentLoading) {
                    this.$snippetEditorArea.append(this.loadingElements[contentLoading]);
                } else {
                    this.el.appendChild(this.loadingElements[contentLoading]);
                }
            };
            if (delay) {
                this.loadingTimers[contentLoading] = setTimeout(addLoader, delay);
            } else {
                addLoader();
            }
            this._mutex.getUnlockedDef().then(() => {
                // Note: we remove the loading element at the end of the
                // execution queue *even if subsequent actions are content
                // related or not*. This is a limitation of the loading feature,
                // the goal is still to limit the number of elements in that
                // queue anyway.
                if (delay) {
                    clearTimeout(this.loadingTimers[contentLoading]);
                    this.loadingTimers[contentLoading] = undefined;
                }

                if (this.loadingElements[contentLoading]) {
                    this.loadingElements[contentLoading].remove();
                    this.loadingElements[contentLoading] = null;
                }
            });
        }
        return mutexExecResult;
    },
    /**
     * Update the options pannel as being empty.
     *
     * TODO review the utility of that function and how to call it (it was not
     * called inside a mutex then we had to do it... there must be better things
     * to do).
     *
     * @private
     */
    _activateEmptyOptionsTab() {
        this._updateRightPanelContent({
            content: this.emptyOptionsTabContent,
            tab: this.tabs.OPTIONS,
            forceEmptyTab: true,
        });
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Activates the right snippet and initializes its SnippetEditor.
     *
     * @private
     */
    _onClick(ev) {
        var srcElement = ev.target || (ev.originalEvent && (ev.originalEvent.target || ev.originalEvent.originalTarget)) || ev.srcElement;
        if (!srcElement || this.lastElement === srcElement) {
            return;
        }
        var $target = $(srcElement);
        // Keep popover open if clicked inside it, but not on a button
        if ($target.parents('.o_edit_menu_popover').length && !$target.parent('a').addBack('a').length) {
            return;
        }
        this.lastElement = srcElement;
        _.defer(() => {
            this.lastElement = false;
        });

        if (!$target.closest('we-button, we-toggler, we-select, .o_we_color_preview').length) {
            this._closeWidgets();
        }
        if (!$target.closest('body > *').length || $target.is('#iframe_target')) {
            return;
        }
        if ($target.closest(this._notActivableElementsSelector).length) {
            return;
        }
        const $oeStructure = $target.closest('.oe_structure');
        if ($oeStructure.length && !$oeStructure.children().length && this.$snippets) {
            // If empty oe_structure, encourage using snippets in there by
            // making them "wizz" in the panel.
            this._activateSnippet(false).then(() => {
                this.$snippets.odooBounce();
            });
            return;
        }
        this._activateSnippet($target);
    },
    /**
     * Called when a child editor asks for insertion zones to be enabled.
     *
     * @private
     * @param {OdooEvent} ev
     */
    _onActivateInsertionZones: function (ev) {
        this._activateInsertionZones(ev.data.$selectorSiblings, ev.data.$selectorChildren, ev.data.canBeSanitizedUnless, ev.data.selectorGrids);
    },
    /**
     * Called when a child editor asks to deactivate the current snippet
     * overlay.
     *
     * @private
     */
    _onActivateSnippet: function (ev) {
        const prom = this._activateSnippet(ev.data.$snippet, ev.data.previewMode, ev.data.ifInactiveOptions);
        if (ev.data.onSuccess) {
            prom.then(() => ev.data.onSuccess());
        }
    },
    /**
     * Called when a child editor asks to operate some operation on all child
     * snippet of a DOM element.
     *
     * @private
     * @param {OdooEvent} ev
     */
    _onCallForEachChildSnippet: function (ev) {
        this._callForEachChildSnippet(ev.data.$snippet, ev.data.callback)
            .then(() => ev.data.onSuccess());
    },
    /**
     * Called when the overlay dimensions/positions should be recomputed.
     *
     * @private
     * @param {OdooEvent} ev
     */
    _onOverlaysCoverUpdate: function (ev) {
        this.snippetEditors.forEach(editor => {
            if (ev.data.overlayVisible) {
                editor.toggleOverlayVisibility(true);
            }
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
        const editor = await this._createSnippetEditor(ev.data.$snippet);
        await editor.clone();
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
    _onDeactivateSnippet: function () {
        this._activateSnippet(false);
    },
    /**
    * Called when a snippet will move in the page.
    *
    * @private
    */
   _onSnippetDragAndDropStart: function () {
        this.snippetEditorDragging = true;
    },
    /**
     * Called when a snippet has moved in the page.
     *
     * @private
     * @param {OdooEvent} ev
     */
    _onSnippetDragAndDropStop: async function (ev) {
        this.snippetEditorDragging = false;
        const $modal = ev.data.$snippet.closest('.modal');
        // If the snippet is in a modal, destroy editors only in that modal.
        // This to prevent the modal from closing because of the cleanForSave
        // on each editors.
        await this._destroyEditors($modal.length ? $modal : null);
        await this._activateSnippet(ev.data.$snippet);
    },
    /**
     * Returns the droppable snippet from which a dropped snippet originates.
     *
     * @private
     * @param {OdooEvent} ev
     */
    _onFindSnippetTemplate(ev) {
        this.$snippets.each(function () {
            const snippetBody = this.querySelector(`.oe_snippet_body[data-snippet=${ev.data.snippet.dataset.snippet}]`);
            if (snippetBody) {
                ev.data.callback(snippetBody.parentElement);
                return false;
            }
        });
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
                            invalidateSnippetCache: true,
                            _toMutex: true,
                            reloadWebClient: true,
                        });
                    }).guardedCatch(reason => {
                        reason.event.preventDefault();
                        this.close();
                        const message = sprintf(Markup(_t("Could not install module <strong>%s</strong>")), name);
                        self.displayNotification({
                            message: message,
                            type: 'danger',
                            sticky: true,
                        });
                    });
                },
            }, {
                text: _t("Install in progress"),
                icon: 'fa-spin fa-circle-o-notch fa-spin mr8',
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
            const editor = await this._createSnippetEditor($snippet);
            return editor.toggleTargetVisibility();
        }, true);
        $(ev.currentTarget).find('.fa')
            .toggleClass('fa-eye', isVisible)
            .toggleClass('fa-eye-slash', !isVisible);
        return this._activateSnippet(isVisible ? $snippet : false);
    },
    /**
     * @private
     */
    _onBlocksTabClick: function (ev) {
        this._activateSnippet(false);
    },
    /**
     * @private
     */
    _onOptionsTabClick: function (ev) {
        if (!ev.currentTarget.classList.contains('active')) {
            this._activateSnippet(false);
            this._mutex.exec(() => {
                this._activateEmptyOptionsTab();
            });
        }
    },
    /**
     * @private
     */
    _onDeleteBtnClick: function (ev) {
        const $snippet = $(ev.target).closest('.oe_snippet');
        const snippetId = parseInt(ev.currentTarget.dataset.snippetId);
        ev.stopPropagation();
        new Dialog(this, {
            size: 'medium',
            title: _t('Confirmation'),
            $content: $('<div><p>' + _.str.sprintf(_t("Are you sure you want to delete the snippet: %s ?"), $snippet.attr('name')) + '</p></div>'),
            buttons: [{
                text: _t("Yes"),
                close: true,
                classes: 'btn-primary',
                click: async () => {
                    await this._rpc({
                        model: 'ir.ui.view',
                        method: 'delete_snippet',
                        kwargs: {
                            'view_id': snippetId,
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
     * @private
     */
    _onRenameBtnClick: function (ev) {
        const $snippet = $(ev.target).closest('.oe_snippet');
        const snippetName = $snippet.attr('name');
        const confirmText = _t('Confirm');
        const cancelText = _t('Cancel');
        const $input = $(`
            <we-input class="o_we_user_value_widget w-100 mx-1">
                <div>
                    <input type="text" autocomplete="chrome-off" value="${snippetName}" class="text-start"/>
                    <we-button class="o_we_confirm_btn o_we_text_success fa fa-check" title="${confirmText}"/>
                    <we-button class="o_we_cancel_btn o_we_text_danger fa fa-times" title="${cancelText}"/>
                </div>
            </we-input>
        `);
        $snippet.find('we-button').remove();
        $snippet.find('span.oe_snippet_thumbnail_title').replaceWith($input);
        const $textInput = $input.find('input');
        $textInput.focus();
        $textInput.select();
        $snippet.find('.oe_snippet_thumbnail').addClass('o_we_already_dragging'); // prevent drag
        $input.find('.o_we_confirm_btn').click(async () => {
            const name = $textInput.val();
            if (name !== snippetName) {
                this._execWithLoadingEffect(async () => {
                    await this._rpc({
                        model: 'ir.ui.view',
                        method: 'rename_snippet',
                        kwargs: {
                            'name': name,
                            'view_id': parseInt(ev.target.dataset.snippetId),
                            'template_key': this.options.snippets,
                        },
                    });
                }, true);
            }
            await this._loadSnippetsTemplates(name !== snippetName);
        });
        $input.find('.o_we_cancel_btn').click(async () => {
            await this._loadSnippetsTemplates(false);
        });
    },
    /**
     * Prevents pointer-events to change the focus when a pointer slide from
     * left-panel to the editable area.
     *
     * @private
     */
    _onMouseDown: function (ev) {
        const $blockedArea = $('#wrapwrap'); // TODO should get that element another way
        this.options.wysiwyg.odooEditor.automaticStepSkipStack();
        $blockedArea.addClass('o_we_no_pointer_events');
        const reenable = () => {
            this.options.wysiwyg.odooEditor.automaticStepSkipStack();
            $blockedArea.removeClass('o_we_no_pointer_events');
        };
        // Use a setTimeout fallback to avoid locking the editor if the mouseup
        // is fired over an element which stops propagation for example.
        const enableTimeoutID = setTimeout(() => reenable(), 5000);
        $(document).one('mouseup', () => {
            clearTimeout(enableTimeoutID);
            reenable();
        });

        const snippetEl = ev.target.closest('.oe_snippet');
        if (snippetEl && !snippetEl.querySelector('.o_we_already_dragging')) {
            this._showSnippetTooltip($(snippetEl));
        }
    },
    /**
     * Displays an autofading tooltip over a snippet, after a delay.
     * If in the meantime the user has started to drag the snippet, it won't be
     * shown.
     *
     * @private
     * @param {jQuery} $snippet
     * @param {Number} [delay=1500]
     */
    _showSnippetTooltip($snippet, delay = 1500) {
        this.__showSnippetTooltip = true;
        setTimeout(() => {
            if (this.__showSnippetTooltip) {
                $snippet.tooltip('show');
                this._hideSnippetTooltips(1500);
            }
        }, delay);
    },
    /**
     * @private
     * @param {Number} [delay=0]
     */
    _hideSnippetTooltips(delay = 0) {
        this.__showSnippetTooltip = false;
        setTimeout(() => {
            this.$snippets.tooltip('hide');
        }, delay);
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
     * UNUSED: used to be called when saving a custom snippet. We now save and
     * reload the page when saving a custom snippet so that all the DOM cleanup
     * mechanisms are run before saving. Kept for compatibility.
     *
     * TODO: remove in master / find a way to clean the DOM without save+reload
     *
     * @private
     */
    _onReloadSnippetTemplate: async function (ev) {
        await this._activateSnippet(false);
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
        const editor = await this._createSnippetEditor(ev.data.$snippet);
        await editor.removeSnippet(ev.data.shouldRecordUndo);
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
        const data = ev.data || {};
        if (ev.target === this && !data._toMutex) {
            return;
        }
        delete data._toMutex;
        ev.stopPropagation();
        this._buttonClick((after) => this._execWithLoadingEffect(() => {
            const oldOnFailure = data.onFailure;
            data.onFailure = () => {
                if (oldOnFailure) {
                    oldOnFailure();
                }
                after();
            };
            this.trigger_up('request_save', data);
        }, true), this.$el[0].querySelector('button[data-action=save]'));
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
    _onSnippetRemoved: function () {
        this._disableUndroppableSnippets();
        this._updateInvisibleDOM();
    },
    /**
     * When the editor panel receives a notification indicating that an option
     * was used, the panel is in charge of asking for an UI update of the whole
     * panel. Logically, the options are displayed so that an option above
     * may influence the status and visibility of an option which is below;
     * e.g.:
     * - the user sets a badge type to 'info'
     *      -> the badge background option (below) is shown as blue
     * - the user adds a shadow
     *      -> more options are shown afterwards to control it (not above)
     *
     * Technically we however update the whole editor panel (parent and child
     * options) wherever the updates comes from. The only important thing is
     * to first update the options UI then their visibility as their visibility
     * may depend on their UI status.
     *
     * @private
     * @param {OdooEvent} ev
     */
    _onSnippetOptionUpdate(ev) {
        ev.stopPropagation();
        (async () => {
            // Only update editors whose DOM target is still inside the document
            // as a top option may have removed currently-enabled child items.
            const editors = this._enabledEditorHierarchy.filter(editor => !!editor.$target[0].closest('body'));

            await Promise.all(editors.map(editor => editor.updateOptionsUI()));
            await Promise.all(editors.map(editor => editor.updateOptionsUIVisibility()));

            // Always enable the deepest editor whose DOM target is still inside
            // the document.
            if (editors[0] !== this._enabledEditorHierarchy[0]) {
                // No awaiting this as the mutex is currently locked here.
                this._activateSnippet(editors[0].$target);
            }

            ev.data.onSuccess();
        })();
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
    _onSnippetThumbnailURLRequest(ev) {
        const $snippet = this.$snippets.has(`[data-snippet="${ev.data.key}"]`);
        ev.data.onSuccess($snippet.length ? $snippet[0].dataset.oeThumbnail : '');
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
    _addToolbar(toolbarMode = "text") {
        let titleText = _t("Inline Text");
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

        this.options.wysiwyg.toolbar.el.classList.remove('oe-floating');

        // Create toolbar custom container.
        this._$toolbarContainer = $('<WE-CUSTOMIZEBLOCK-OPTIONS id="o_we_editor_toolbar_container"/>');
        const $title = $("<we-title><span>" + titleText + "</span></we-title>");

        this._$toolbarContainer.append($title);
        this._$toolbarContainer.append(this.options.wysiwyg.toolbar.$el);
        $(this.customizePanel).append(this._$toolbarContainer);

        // Create table-options custom container.
        const $customizeTableBlock = $(QWeb.render('web_editor.toolbar.table-options'));
        this.options.wysiwyg.odooEditor.bindExecCommand($customizeTableBlock[0]);

        $(this.customizePanel).append($customizeTableBlock);

        this._$removeFormatButton = this._$removeFormatButton || this.options.wysiwyg.toolbar.$el.find('#removeFormat');
        $title.append(this._$removeFormatButton);
        this.options.wysiwyg.toolbar.$el.find('#table').remove();

        this._checkEditorToolbarVisibility();
    },
    /**
     * Update editor UI visibility based on the current range.
     */
    _checkEditorToolbarVisibility: function (e) {
        const $toolbarContainer = this.$('#o_we_editor_toolbar_container');
        const $toolbarTableContainer = this.$('#o-we-editor-table-container');
        const selection = this.options.wysiwyg.odooEditor.document.getSelection();
        const range = selection && selection.rangeCount && selection.getRangeAt(0);
        const $currentSelectionTarget = $(range && range.commonAncestorContainer);
        // Do not  toggle visibility if the target is inside the toolbar ( eg.
        // during link edition).
        if ($currentSelectionTarget.closest('#o_we_editor_toolbar_container').length ||
            (e && $(e.target).closest('#o_we_editor_toolbar_container').length)
        ) {
            return;
        }
        if (!range ||
            !$currentSelectionTarget.parents('#wrapwrap, .iframe-editor-wrapper .o_editable').length ||
            $(selection.anchorNode).parent('[data-oe-model]:not([data-oe-type="html"]):not([data-oe-field="arch"]):not([data-oe-translation-initial-sha])').length ||
            $(selection.focusNode).parent('[data-oe-model]:not([data-oe-type="html"]):not([data-oe-field="arch"]):not([data-oe-translation-initial-sha])').length ||
            (e && $(e.target).closest('.fa, img').length ||
            this.options.wysiwyg.lastMediaClicked && $(this.options.wysiwyg.lastMediaClicked).is('.fa, img')) ||
            (this.options.wysiwyg.lastElement && !this.options.wysiwyg.lastElement.isContentEditable)
        ) {
            $toolbarContainer.hide();
        } else {
            $toolbarContainer.show();
        }

        const isInsideTD = !!(
            range &&
            $(range.startContainer).closest('.o_editable td').length &&
            $(range.endContainer).closest('.o_editable td').length
        );
        $toolbarTableContainer.toggleClass('d-none', !isInsideTD);
    },
    /**
     * On click on discard button.
     */
    _onDiscardClick: function () {
        this._buttonClick(after => {
            this.snippetEditors.forEach(editor => {
                editor.toggleOverlay(false);
            });
            this.trigger_up('request_cancel', {onReject: after});
        }, this.$el[0].querySelector('button[data-action=cancel]'), false);
    },
    /**
     * Preview on mobile.
     */
    _onMobilePreviewClick() {
        this.trigger_up('request_mobile_preview');

        // TODO refactor things to make this more understandable -> on mobile
        // edition, update the UI. But to do it properly and inside the mutex
        // this simulates what happens when a snippet option is used.
        this._execWithLoadingEffect(async () => {
            // TODO needed so that mobile edition is considered before updating
            // the UI but this is clearly random. The trigger_up above should
            // properly await for the rerender somehow.
            await new Promise(resolve => setTimeout(resolve));

            return new Promise(resolve => {
                this.trigger_up('snippet_option_update', {
                    onSuccess: () => resolve(),
                });
            });
        }, false);

        // Reload images inside grid items so that no image disappears when
        // activating mobile preview.
        const gridItemEls = this.getEditableArea().find('div.o_grid_item');
        for (const gridItemEl of gridItemEls) {
            gridUtils._reloadLazyImages(gridItemEl);
        }
    },
    /**
     * Undo..
     */
    _onUndo: async function () {
        this.options.wysiwyg.undo();
        // Resizing all the grids.
        // TODO maybe to remove when history will be fixed.
        const $gridModeRows = this.getEditableArea().find('.row.o_grid_mode');
        for (const rowEl of $gridModeRows) {
            gridUtils._resizeGrid(rowEl);
        }
    },
    /**
     * Redo.
     */
    _onRedo: async function () {
        this.options.wysiwyg.redo();
        // Resizing all the grids.
        // TODO maybe to remove when history will be fixed.
        const $gridModeRows = this.getEditableArea().find('.row.o_grid_mode');
        for (const rowEl of $gridModeRows) {
            gridUtils._resizeGrid(rowEl);
        }
    },
    /**
     * @private
     * @param {OdooEvent} ev
     */
    _onRequestEditable: function (ev) {
        ev.data.callback($(this.options.wysiwyg.odooEditor.editable));
    },
    /**
     * Enable loading effects
     *
     * @private
     */
    _onEnableLoadingEffect: function () {
        this._loadingEffectDisabled = false;
    },
    /**
     * Disable loading effects and cancel the one displayed
     *
     * @private
     */
    _onDisableLoadingEffect: function () {
        this._loadingEffectDisabled = true;
        Object.keys(this.loadingElements).forEach(key => {
            if (this.loadingElements[key]) {
                this.loadingElements[key].remove();
                this.loadingElements[key] = null;
            }
        });
    },
    /***
     * Display a loading effect on the clicked button, and disables the other
     * buttons. Passes an argument to restore the buttons to their normal
     * state to the function to execute.
     *
     * @param action {Function} The action to execute
     * @param button {HTMLElement} The button element
     * @param addLoadingEffect {boolean} whether or not to add a loading effect.
     * @returns {Promise<void>}
     * @private
     */
    async _buttonClick(action, button, addLoadingEffect = true) {
        if (this._buttonAction) {
            return;
        }
        this._buttonAction = true;
        let removeLoadingEffect;
        if (addLoadingEffect) {
            removeLoadingEffect = dom.addButtonLoadingEffect(button);
        }
        const actionButtons = this.$el[0].querySelectorAll('[data-action]');
        for (const actionButton of actionButtons) {
            actionButton.disabled = true;
        }
        const after = () => {
            if (removeLoadingEffect) {
                removeLoadingEffect();
            }
            for (const actionButton of actionButtons) {
                actionButton.disabled = false;
            }
        };
        await action(after);
        this._buttonAction = false;
    },
});

return {
    SnippetsMenu: SnippetsMenu,
    SnippetEditor: SnippetEditor,
    globalSelector: globalSelector,
};
});
