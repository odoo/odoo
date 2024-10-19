/** @odoo-module **/

import { Mutex } from "@web/core/utils/concurrency";
import { clamp } from "@web/core/utils/numbers";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import dom from "@web/legacy/js/core/dom";
import { session } from "@web/session";
import Widget from "@web/legacy/js/core/widget";
import { useDragAndDrop } from "@web_editor/js/editor/drag_and_drop";
import options from "@web_editor/js/editor/snippets.options";
import weUtils from "@web_editor/js/common/utils";
import * as gridUtils from "@web_editor/js/common/grid_layout_utils";
import { escape } from "@web/core/utils/strings";
import { closestElement, isUnremovable } from "@web_editor/js/editor/odoo-editor/src/utils/utils";
import { debounce, throttleForAnimation } from "@web/core/utils/timing";
import { uniqueId } from "@web/core/utils/functions";
import { sortBy, unique } from "@web/core/utils/arrays";
import { browser } from "@web/core/browser/browser";
import { attachComponent } from "@web/legacy/utils";
import { Toolbar } from "@web_editor/js/editor/toolbar";
import {
    Component,
    markup,
    xml,
} from "@odoo/owl";
import { LinkTools } from '@web_editor/js/wysiwyg/widgets/link_tools';
import { touching, closest } from "@web/core/utils/ui";
import { _t } from "@web/core/l10n/translation";
import { pyToJsLocale } from "@web/core/l10n/utils";
import { renderToElement } from "@web/core/utils/render";
import { RPCError } from "@web/core/network/rpc_service";
import { ColumnLayoutMixin } from "@web_editor/js/common/column_layout_mixin";

let cacheSnippetTemplate = {};

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
        // This is possible to have a snippet editor not inside an editable area
        // (data-no-check="true") and it is possible to not have editable areas
        // at all (restricted editor), in that case we just suppose this is the
        // body so related code can still be executed without crash (as we still
        // need to instantiate instances of editors even if nothing is really
        // editable (data-no-check="true" / navigation options / ...)).
        // TODO this should probably be reviewed in master: do we need a
        // reference to the editable area? There should be workarounds.
        this.$editable = $editable && $editable.length ? $editable : $(document.body);
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
        this.isTargetRemovable = this.isTargetParentEditable && !this.$target.parent().is('[data-oe-type="image"]') && !isUnremovable(this.$target[0]);
        this.displayOverlayOptions = this.displayOverlayOptions || this.isTargetMovable || !this.isTargetParentEditable;

        // Initialize move/clone/remove buttons
        if (this.isTargetMovable) {
            this.dropped = false;
            this.draggableComponent = this._initDragAndDrop(".o_move_handle", ".oe_overlay", this.el);
            if (!this.$target[0].matches("section")) {
                // Allow the user to drag the image itself to move the target.
                // Note that the o_draggable class will be added by the
                // _initDragAndDrop function. So adding it here is probably
                // useless. To check. The fact that that class is added in any
                // case should probably reviewed in master anyway (TODO).
                this.$target[0].classList.add("o_draggable");
                this.draggableComponentImgs = this._initDragAndDrop("img", ".o_draggable", this.$target[0]);
            }
        } else {
            this.$('.o_overlay_move_options').addClass('d-none');
            const cloneButtonEl = $customize[0].querySelector(".oe_snippet_clone");
            cloneButtonEl.classList.toggle("d-none", !this.forceDuplicateButton);
        }

        if (!this.isTargetRemovable) {
            this.$el.add($customize).find('.oe_snippet_remove').addClass('d-none');
        }

        var _animationsCount = 0;
        this.postAnimationCover = throttleForAnimation(() => {
            this.trigger_up('cover_update', {
                overlayVisible: true,
            });
        });
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
                    this.postAnimationCover();
                }
            }, 500); // This delay have to be huge enough to take care of long
                     // animations which will not trigger an animation end event
                     // but if it is too small for some, this is the job of the
                     // animation creator to manually ask for a re-cover
        });
        // On top of what is explained above, do the post animation cover for
        // each detected transition/animation end so that the user does not see
        // a flickering when not needed.
        this.$target.on('transitionend.snippet_editor, animationend.snippet_editor', this.postAnimationCover);

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
        this.draggableComponent && this.draggableComponent.destroy();
        this.draggableComponentImgs?.destroy();
        if (this.$optionsSection) {
            this.$optionsSection.remove();
        }
        if (this.postAnimationCover) {
            this.postAnimationCover.cancel();
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
     *
     * @param {HTMLElement} targetEl the snippet dropped in the page
     */
    async buildSnippet(targetEl) {
        for (var i in this.styles) {
            await this.styles[i].onBuilt({
                isCurrent: targetEl === this.$target[0],
            });
        }
        // TODO In master differentiate device-based visibility.
        this._toggleVisibilityStatusIgnoreDeviceVisibility = true;
        await this.toggleTargetVisibility(true);
        this._toggleVisibilityStatusIgnoreDeviceVisibility = false;
    },
    /**
     * Notifies all the associated snippet options that the template which
     * contains the snippet is about to be saved.
     */
    cleanForSave: async function () {
        if (this.isDestroyed()) {
            return;
        }
        await this.toggleTargetVisibility(!this.$target.hasClass('o_snippet_invisible')
            && !this.$target.hasClass('o_snippet_mobile_invisible')
            && !this.$target.hasClass('o_snippet_desktop_invisible'));
        const proms = Object.values(this.styles).map((option) => {
            return option.cleanForSave();
        });
        await Promise.all(proms);
        await this.cleanUI();
    },
    /**
     * Notifies all the associated snippet options that the snippet UI needs to
     * be cleaned.
     */
    async cleanUI() {
        const proms = Object.values(this.styles).map((option) => {
            return option.cleanUI();
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
        // TODO: At that point, targetEl.ownerDocument.defaultView should not be
        // null. However, there is a non-deterministic race condition that can
        // result in the document being unloaded from the iframe before the handlers
        // of the snippets menu are removed, thus triggering a traceback if the
        // optional chaining operator is removed. This can be reproduced
        // non-deterministically on runbot by running the edit_menus tour.
        const vpWidth = targetEl.ownerDocument.defaultView?.innerWidth || document.documentElement.clientWidth;
        const vpHeight = targetEl.ownerDocument.defaultView?.innerHeight || document.documentElement.clientHeight;
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

        // The manipulator is supposed to follow the scroll of the content
        // naturally without any JS recomputation.
        const manipulatorOffset = this.$el.parent().offset();
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
        // If the element covered by the overlay has a scrollbar, we remove its
        // right border as it interferes with proper scrolling. (e.g. modal)
        const handleEReadonlyEl = this.$el[0].querySelector('.o_handle.e.readonly');
        if (handleEReadonlyEl) {
            handleEReadonlyEl.style.width = $(targetEl).hasScrollableContent() ? 0 : '';
        }
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
        if (this.$target[0].matches(".btn")) {
            return _t("Button");
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
                return isEmpty && !$el.hasClass('oe_structure')
                    && !$el.parent().hasClass('carousel-item')
                    && (!editor || editor.isTargetParentEditable)
                    && !isUnremovable($el[0]);
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
            const styles = sortBy(Object.values(editor.styles || {}), "__order");
            await focusOrBlur(editor, styles);
        }
        await Promise.all(editorUIsToUpdate.map(editor => editor.updateOptionsUI()));
        await Promise.all(editorUIsToUpdate.map(editor => editor.updateOptionsUIVisibility()));

        // As the 'd-none' class is added to option sections that have no visible
        // options with 'updateOptionsUIVisibility', if no option section is
        // visible, we prevent the activation of the options.
        // Special case: For now, we only allow activating text options in
        // translate mode (with no parent editors). These text options have a
        // special way to be displayed in the editor: We add the options in the
        // toolbar `onFocus()` and set them back `onBlur()`. Which means the
        // options section will be empty and get a `d-none` class, while
        // actually it has visible options (they are just added in the toolbar
        // DOM). We need to take them into consideration to display options in
        // translate mode correctly.
        const optionsSectionVisible = editorUIsToUpdate.some(editor =>
            !editor.$optionsSection[0].classList.contains("d-none") ||
            Object.keys(editor.styles).some(key =>
                editor.styles[key].el.closest(".oe-toolbar")
            )
        );
        if (editorUIsToUpdate.length > 0 && !optionsSectionVisible) {
            return null;
        }
        return this._customize$Elements;
    },
    /**
     * @param {boolean} [show]
     * @returns {Promise<boolean>}
     */
    toggleTargetVisibility: async function (show) {
        show = this._toggleVisibilityStatus(show);
        var styles = Object.values(this.styles);
        const proms = sortBy(styles, "__order").map((style) => {
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
     * @param {boolean} [assetsChanged=false]
     * @returns {Promise}
     */
    async updateOptionsUI(assetsChanged) {
        const proms = Object.values(this.styles).map(opt => {
            return opt.updateUI({noVisibility: true, assetsChanged: assetsChanged});
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
        await Promise.all(proms);
        // Hide the snippetEditor if none of its options are visible
        // This cannot be done using the visibility of the options' UI
        // because some options can be located in the overlay.
        const $visibleOptions = this.$optionsSection.find('we-top-button-group, we-customizeblock-option')
                .children(':not(.d-none)');
        this.$optionsSection.toggleClass('d-none', !$visibleOptions.length);
    },
    /**
     * Clones the current snippet.
     *
     * @param {boolean} recordUndo
     */
    clone: async function (recordUndo) {
        this.trigger_up('snippet_will_be_cloned', {$target: this.$target});

        await new Promise(resolve => {
            this.trigger_up("clean_ui_request", {
                targetEl: this.$target[0],
                onSuccess: resolve,
            });
        });

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
        this.selectorLockWithin = new Set();
        const selectorExcludeAncestor = new Set();

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

        var $optionsSection = $(renderToElement('web_editor.customize_block_options_section', {
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
        var defs = this.templateOptions.map((val) => {
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
            if (val['drop-lock-within']) {
                this.selectorLockWithin.add(val['drop-lock-within']);
            }
            if (val['drop-exclude-ancestor']) {
                selectorExcludeAncestor.add(val['drop-exclude-ancestor']);
            }

            var optionName = val.option;
            var option = new (options.registry[optionName] || options.Class)(
                this,
                val.$el.children(),
                val.base_target ? this.$target.find(val.base_target).eq(0) : this.$target,
                this.$el,
                Object.assign({
                    optionName: optionName,
                    snippetName: this.getName(),
                }, val.data),
                this.options
            );
            var key = optionName || uniqueId("option");
            if (this.styles[key]) {
                // If two snippet options use the same option name (and so use
                // the same JS option), store the subsequent ones with a unique
                // ID (TODO improve)
                key = uniqueId(key);
            }
            this.styles[key] = option;
            option.__order = i++;

            if (option.forceNoDeleteButton) {
                this.$el.add($optionsSection).find('.oe_snippet_remove').addClass('d-none');
                this.$el.add($optionsSection).find('.oe_snippet_clone').addClass('d-none');
            }

            if (option.displayOverlayOptions) {
                this.displayOverlayOptions = true;
            }

            if (option.forceDuplicateButton) {
                this.forceDuplicateButton = true;
            }

            return option.appendTo(document.createDocumentFragment());
        });

        if (selectorExcludeAncestor.size) {
            // Prevents dropping an element into another one.
            // (E.g. ToC inside another ToC)
            const excludedAncestorSelector = [...selectorExcludeAncestor].join(", ");
            this.excludeAncestors = (i, el) => !el.closest(excludedAncestorSelector);
        }

        this.isTargetMovable = (this.selectorSiblings.length > 0 || this.selectorChildren.length > 0);

        this.$el.find('[data-bs-toggle="dropdown"]').dropdown();

        return Promise.all(defs).then(async () => {
            const options = sortBy(Object.values(this.styles), "__order");
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
     * Initialize drag and drop handlers.
     *
     * @private
     * @param {String} handle css selector for grabble element
     * @param {String} elementsSelector selector for elements that will be dragged.
     * @param {HTMLElement} element element to listen for drag events.
     * @returns {Object} the drag state.
     */
    _initDragAndDrop(handle, elementsSelector, element) {
        const modalAncestorEl = this.$target[0].closest('.modal');
        const $scrollable = modalAncestorEl && $(modalAncestorEl)
            || (this.options.wysiwyg.snippetsMenu && this.options.wysiwyg.snippetsMenu.$scrollable)
            || (this.$scrollingElement.length && this.$scrollingElement)
            || $().getScrollingElement(this.ownerDocument);
        const dragAndDropOptions = {
            ref: { el: element },
            elements: elementsSelector,
            handle: handle,
            scrollingElement: $scrollable[0],
            enable: () => !!this.$el.find('.o_move_handle:visible').length || this.dragStarted,
            helper: () => {
                const cloneEl = this.$el[0].cloneNode(true);
                cloneEl.style.width = "24px";
                cloneEl.style.height = "24px";
                cloneEl.style.border = "0";
                this.$el[0].ownerDocument.body.appendChild(cloneEl);
                cloneEl.classList.remove("d-none");
                cloneEl.classList.remove("o_dragged");
                return cloneEl;
            },
            onDragStart: (args) => {
                this.dragStarted = true;
                const targetRect = this.$target[0].getBoundingClientRect();
                // Bound the Y mouse position to the element height minus one
                // grid row, to be able to drag from the bottom in a grid.
                const gridRowSize = gridUtils.rowSize;
                const boundedYMousePosition = Math.min(args.y, targetRect.bottom - gridRowSize);
                this.mousePositionYOnElement = boundedYMousePosition - targetRect.y;
                this.mousePositionXOnElement = args.x - targetRect.x;
                this._onDragAndDropStart(args);
            },
            onDragEnd: (...args) => {
                if (!this.dragStarted) {
                    return false;
                }
                this.dragStarted = false;
                // Delay our stop handler so that some wysiwyg handlers
                // which occur on mouseup (and are themself delayed) are
                // executed first (this prevents the library to crash
                // because our stop handler may change the DOM).
                setTimeout(() => {
                    this._onDragAndDropStop(...args);
                }, 0);
            },
            onDrag: this._onDragMove.bind(this),
            dropzoneOver: this.dropzoneOver.bind(this),
            dropzoneOut: this.dropzoneOut.bind(this),
            dropzones: () => this.$dropZones?.toArray() || [],
        };
        const finalOptions = this.options.getDragAndDropOptions(dragAndDropOptions);
        return useDragAndDrop(finalOptions);
    },
    /**
     * @private
     * @param {boolean} [show]
     */
    _toggleVisibilityStatus: function (show) {
        // TODO In master differentiate device-based visibility.
        if (this._toggleVisibilityStatusIgnoreDeviceVisibility) {
            if (this.$target[0].matches(".o_snippet_mobile_invisible, .o_snippet_desktop_invisible")) {
                const isMobilePreview = weUtils.isMobileView(this.$target[0]);
                const isMobileHidden = this.$target[0].classList.contains("o_snippet_mobile_invisible");
                if (isMobilePreview === isMobileHidden) {
                    // Preview mode and hidden type are the same.
                    show = false;
                }
            }
        }
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
    /**
     * Called when an "over" dropzone event happens after an other "over"
     * without an "out" between them. It escapes the previous dropzone.
     *
     * @private
     * @param {Object} self
     *      the same `self` variable as when we are in `_onDragAndDropStart`
     * @param {Element} currentDropzoneEl
     *      the dropzone over which we are currently dragging
     */
    _outPreviousDropzone(self, currentDropzoneEl) {
        const previousDropzoneEl = this;
        const rowEl = previousDropzoneEl.parentNode;

        if (rowEl.classList.contains('o_grid_mode')) {
            self.dragState.gridMode = false;
            const fromGridToGrid = currentDropzoneEl.classList.contains('oe_grid_zone');
            if (fromGridToGrid) {
                // If we went from a grid dropzone to an other grid one.
                rowEl.style.removeProperty('position');
            } else {
                // If we went from a grid dropzone to a normal one.
                gridUtils._gridCleanUp(rowEl, self.$target[0]);
                self.$target[0].style.removeProperty('z-index');
            }

            // Removing the drag helper and the background grid and
            // resizing the grid and the dropzone.
            self.dragState.dragHelperEl.remove();
            self.dragState.backgroundGridEl.remove();
            self.options.wysiwyg.odooEditor.observerActive('dragAndDropMoveSnippet');
            gridUtils._resizeGrid(rowEl);
            self.options.wysiwyg.odooEditor.observerUnactive('dragAndDropMoveSnippet');
            const rowCount = parseInt(rowEl.dataset.rowCount);
            previousDropzoneEl.style.gridRowEnd = Math.max(rowCount + 1, 1);
        }
        previousDropzoneEl.classList.remove('invisible');
    },
    /**
     * Changes some behaviors before the drag and drop.
     *
     * @private
     * @returns {Function} a function that restores what was changed when the
     *  drag and drop is over.
     */
    _prepareDrag() {
        return () => {};
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
    _onDragAndDropStart({ helper, addStyle }) {
        this.options.wysiwyg.odooEditor.observerUnactive('dragAndDropMoveSnippet');
        this.trigger_up('drag_and_drop_start');
        this.options.wysiwyg.odooEditor.automaticStepUnactive();
        var self = this;
        this.dragState = {};
        const rowEl = this.$target[0].parentNode;
        this.dragState.overFirstDropzone = true;

        this.dragState.restore = this._prepareDrag();

        // Allow the grid mode if the option is present in the right panel or
        // if the grid mode is already activated.
        let hasGridLayoutOption = false;
        this.trigger_up('user_value_widget_request', {
            name: 'grid_mode',
            allowParentOption: true,
            onSuccess: (widget) => {
                // The grid option is considered as present only if the
                // container element having it is the same as the container of
                // the column we are dragging.
                if (widget.$target[0] === rowEl.parentElement) {
                    hasGridLayoutOption = true;
                }
            },
        });
        const allowGridMode = hasGridLayoutOption || rowEl.classList.contains('o_grid_mode');

        // Number of grid columns and rows in the grid item (BS column).
        if (rowEl.classList.contains('row') && this.options.isWebsite) {
            if (allowGridMode) {
                // Toggle grid mode if it is not already on.
                if (!rowEl.classList.contains('o_grid_mode')) {
                    this.options.wysiwyg.odooEditor.observerActive('dragAndDropMoveSnippet');
                    const containerEl = rowEl.parentNode;
                    gridUtils._toggleGridMode(containerEl);
                    this.options.wysiwyg.odooEditor.observerUnactive('dragAndDropMoveSnippet');
                }

                // Computing the moving column width and height in terms of columns
                // and rows.
                const columnStart = self.$target[0].style.gridColumnStart;
                const columnEnd = self.$target[0].style.gridColumnEnd;
                const rowStart = self.$target[0].style.gridRowStart;
                const rowEnd = self.$target[0].style.gridRowEnd;

                this.dragState.columnColCount = columnEnd - columnStart;
                this.dragState.columnRowCount = rowEnd - rowStart;

                // Storing the current grid and grid area to use them for the
                // history.
                this.dragState.startingGrid = rowEl;
                this.dragState.prevGridArea = self.$target[0].style.gridArea;

                this.dragState.startingZIndex = self.$target[0].style.zIndex;

                // Reload the images.
                gridUtils._reloadLazyImages(this.$target[0]);
            } else {
                // If the column comes from a snippet that doesn't toggle the
                // grid mode on drag, store its width and height to use them
                // when the column goes over a grid dropzone.
                const isImageColumn = gridUtils._checkIfImageColumn(this.$target[0]);
                if (isImageColumn) {
                    // Store the image width and height if the column only
                    // contains an image.
                    const imageEl = this.$target[0].querySelector('img');
                    this.dragState.columnWidth = parseFloat(imageEl.scrollWidth);
                    this.dragState.columnHeight = parseFloat(imageEl.scrollHeight);
                } else {
                    this.dragState.columnWidth = parseFloat(this.$target[0].scrollWidth);
                    this.dragState.columnHeight = parseFloat(this.$target[0].scrollHeight);
                }
                // Taking the column borders into account.
                const style = window.getComputedStyle(this.$target[0]);
                this.dragState.columnWidth += parseFloat(style.borderLeft) + parseFloat(style.borderRight);
                this.dragState.columnHeight += parseFloat(style.borderTop) + parseFloat(style.borderBottom);
            }
            // Storing the starting top position of the column.
            this.dragState.columnTop = this.$target[0].getBoundingClientRect().top;
            this.dragState.isColumn = true;
            // Deactivate the snippet so the overlay doesn't show.
            this.trigger_up('deactivate_snippet', {$snippet: self.$target});
        }

        // If the target has a mobile order class, store its parent and order.
        const targetMobileOrder = this.$target[0].style.order;
        if (targetMobileOrder) {
            this.dragState.startingParent = this.$target[0].parentNode;
            this.dragState.mobileOrder = parseInt(targetMobileOrder);
        }

        const toInsertInline = window.getComputedStyle(this.$target[0]).display.includes('inline');

        this.dropped = false;
        this._dropSiblings = {
            prev: self.$target.prev()[0],
            next: self.$target.next()[0],
        };
        self.size = {
            width: self.$target.width(),
            height: self.$target.height()
        };
        const dropCloneEl = document.createElement("div");
        dropCloneEl.classList.add("oe_drop_clone");
        dropCloneEl.style.setProperty("display", "none");
        self.$target[0].after(dropCloneEl);
        self.$target.detach();
        self.$el.addClass('d-none');

        var $selectorSiblings;
        for (var i = 0; i < self.selectorSiblings.length; i++) {
            let $siblings = self.selectorSiblings[i].all();
            if (this.excludeAncestors) {
                $siblings = $siblings.filter(this.excludeAncestors);
            }
            $selectorSiblings = $selectorSiblings ? $selectorSiblings.add($siblings) : $siblings;
        }
        var $selectorChildren;
        for (i = 0; i < self.selectorChildren.length; i++) {
            let $children = self.selectorChildren[i].all();
            if (this.excludeAncestors) {
                $children = $children.filter(this.excludeAncestors);
            }
            $selectorChildren = $selectorChildren ? $selectorChildren.add($children) : $children;
        }
        // Disallow dropping an element outside a given direct or
        // indirect parent. (E.g. form field must remain within its own form)
        for (const lockedParentSelector of this.selectorLockWithin) {
            const closestLockedParentEl = dropCloneEl.closest(lockedParentSelector);
            const filterFunc = (i, el) => el.closest(lockedParentSelector) === closestLockedParentEl;
            if ($selectorSiblings) {
                $selectorSiblings = $selectorSiblings.filter(filterFunc);
            }
            if ($selectorChildren) {
                $selectorChildren = $selectorChildren.filter(filterFunc);
            }
        }

        const canBeSanitizedUnless = this._canBeSanitizedUnless(this.$target[0]);

        // Remove the siblings/children that would add a dropzone as direct
        // child of a grid area and make a dedicated set out of the identified
        // grid areas.
        const selectorGrids = new Set();
        const filterOutSelectorGrids = ($selectorItems, getDropzoneParent) => {
            if (!$selectorItems) {
                return;
            }
            // Looping backwards because elements are removed, so the
            // indexes are not lost.
            for (let i = $selectorItems.length - 1; i >= 0; i--) {
                const el = getDropzoneParent($selectorItems[i]);
                if (el.classList.contains('o_grid_mode')) {
                    $selectorItems.splice(i, 1);
                    selectorGrids.add(el);
                }
            }
        };
        filterOutSelectorGrids($selectorSiblings, el => el.parentElement);
        filterOutSelectorGrids($selectorChildren, el => el);

        this.trigger_up('activate_snippet', {$snippet: this.$target.parent()});
        this.trigger_up('activate_insertion_zones', {
            $selectorSiblings: $selectorSiblings,
            $selectorChildren: $selectorChildren,
            canBeSanitizedUnless: canBeSanitizedUnless,
            toInsertInline: toInsertInline,
            selectorGrids: selectorGrids,
            fromIframe: true,
        });

        this.$body.addClass('move-important');

        this.$dropZones = this.$editable.find('.oe_drop_zone');
        if (!canBeSanitizedUnless) {
            this.$dropZones = this.$dropZones.not('[data-oe-sanitize] .oe_drop_zone');
        } else if (canBeSanitizedUnless === 'form') {
            this.$dropZones = this.$dropZones.not('[data-oe-sanitize][data-oe-sanitize!="allow_form"] .oe_drop_zone');
        }
    },
    dropzoneOver({ dropzone }) {
        if (this.dropped) {
            this.$target.detach();
        }

        // Prevent a column to be trapped in an upper grid dropzone at
        // the start of the drag.
        if (this.dragState.isColumn && this.dragState.overFirstDropzone) {
            this.dragState.overFirstDropzone = false;

            // The column is considered as glued to the dropzone if the
            // dropzone is above and if the space between them is less
            // than 25px (the move handle height is 22px so 25 is a
            // safety margin).
            const columnTop = this.dragState.columnTop;
            const dropzoneBottom = dropzone.el.getBoundingClientRect().bottom;
            const areDropzonesGlued = (columnTop >= dropzoneBottom) && (columnTop - dropzoneBottom < 25);

            if (areDropzonesGlued && dropzone.el.classList.contains('oe_grid_zone')) {
                return;
            }
        }

        this.dropped = true;
        const $dropzone = $(dropzone.el).first().after(this.$target);
        $dropzone.addClass('invisible');

        // Checking if the "out" event happened before dropzone.el "over": if
        // `this.dragState.currentDropzoneEl` exists, "out" didn't
        // happen because it deletes it. We are therefore in the case
        // of an "over" after an "over" and we need to escape the
        // previous dropzone first.
        if (this.dragState.currentDropzoneEl) {
            this._outPreviousDropzone.apply(this.dragState.currentDropzoneEl, [this, $dropzone[0]]);
        }
        this.dragState.currentDropzoneEl = $dropzone[0];

        if ($dropzone[0].classList.contains('oe_grid_zone')) {
            // Case where the column we are dragging is over a grid
            // dropzone.
            const rowEl = $dropzone[0].parentNode;

            // If the column doesn't come from a grid mode snippet.
            if (!this.$target[0].classList.contains('o_grid_item')) {
                // Converting the column to grid.
                this.options.wysiwyg.odooEditor.observerActive('dragAndDropMoveSnippet');
                const spans = gridUtils._convertColumnToGrid(rowEl, this.$target[0], this.dragState.columnWidth, this.dragState.columnHeight);
                this.options.wysiwyg.odooEditor.observerUnactive('dragAndDropMoveSnippet');
                this.dragState.columnColCount = spans.columnColCount;
                this.dragState.columnRowCount = spans.columnRowCount;

                // Storing the column spans.
            }

            const columnColCount = this.dragState.columnColCount;
            const columnRowCount = this.dragState.columnRowCount;
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

            this.options.wysiwyg.odooEditor.observerActive('dragAndDropMoveSnippet');
            // Setting the moving grid item, the background grid and
            // the drag helper z-indexes. The grid item z-index is set
            // to its original one if we are in its starting grid, or
            // to the maximum z-index of the grid otherwise.
            if (rowEl === this.dragState.startingGrid) {
                this.$target[0].style.zIndex = this.dragState.startingZIndex;
            } else {
                gridUtils._setElementToMaxZindex(this.$target[0], rowEl);
            }
            gridUtils._setElementToMaxZindex(backgroundGridEl, rowEl);
            gridUtils._setElementToMaxZindex(dragHelperEl, rowEl);

            // Setting the column height and width to keep its size
            // when the grid-area is removed (as it prevents it from
            // moving with the mouse).
            const gridProp = gridUtils._getGridProperties(rowEl);
            const columnHeight = columnRowCount * (gridProp.rowSize + gridProp.rowGap) - gridProp.rowGap;
            const columnWidth = columnColCount * (gridProp.columnSize + gridProp.columnGap) - gridProp.columnGap;
            this.$target[0].style.height = columnHeight + 'px';
            this.$target[0].style.width = columnWidth + 'px';
            this.$target[0].style.position = 'absolute';
            this.$target[0].style.removeProperty('grid-area');
            rowEl.style.position = 'relative';
            this.options.wysiwyg.odooEditor.observerUnactive('dragAndDropMoveSnippet');

            // Storing useful information and adding an event listener.
            this.dragState.startingHeight = rowEl.clientHeight;
            this.dragState.currentHeight = rowEl.clientHeight;
            this.dragState.dragHelperEl = dragHelperEl;
            this.dragState.backgroundGridEl = backgroundGridEl;
            this.dragState.gridMode = true;
        }
    },
    dropzoneOut({ dropzone }) {
        const rowEl = dropzone.el.parentNode;

        // Checking if the "out" event happens right after the "over"
        // of the same dropzone. If it is not the case, we don't do
        // anything since the previous dropzone was already escaped (at
        // the start of the over).
        const sameDropzoneAsCurrent = this.dragState.currentDropzoneEl === dropzone.el;

        if (sameDropzoneAsCurrent) {
            if (rowEl.classList.contains('o_grid_mode')) {
                // Removing the listener + cleaning.
                this.dragState.gridMode = false;
                gridUtils._gridCleanUp(rowEl, this.$target[0]);
                this.$target[0].style.removeProperty('z-index');

                // Removing the drag helper and the background grid and
                // resizing the grid and the dropzone.
                this.dragState.dragHelperEl.remove();
                this.dragState.backgroundGridEl.remove();
                this.options.wysiwyg.odooEditor.observerActive('dragAndDropMoveSnippet');
                gridUtils._resizeGrid(rowEl);
                this.options.wysiwyg.odooEditor.observerUnactive('dragAndDropMoveSnippet');
                const rowCount = parseInt(rowEl.dataset.rowCount);
                dropzone.el.style.gridRowEnd = Math.max(rowCount + 1, 1);
            }

            var prev = this.$target.prev();
            if (dropzone.el === prev[0]) {
                this.dropped = false;
                this.$target.detach();
                $(dropzone.el).removeClass('invisible');
            }

            delete this.dragState.currentDropzoneEl;
        }
    },
    /**
     * Called when the snippet is dropped after being dragged thanks to the
     * 'move' button.
     *
     * @private
     * @param {Event} ev
     * @param {Object} ui
     */
    _onDragAndDropStop({ x, y }) {
        this.options.wysiwyg.odooEditor.automaticStepActive();
        this.options.wysiwyg.odooEditor.automaticStepSkipStack();
        this.options.wysiwyg.odooEditor.unbreakableStepUnactive();

        const rowEl = this.$target[0].parentNode;
        if (rowEl && rowEl.classList.contains('o_grid_mode')) {
            // Case when dropping the column in a grid.

            // Disable dragMove handler
            this.dragState.gridMode = false;

            // Defining the column grid area with its position.
            const gridProp = gridUtils._getGridProperties(rowEl);

            const style = window.getComputedStyle(this.$target[0]);
            const top = parseFloat(style.top);
            const left = parseFloat(style.left);

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
            this.options.wysiwyg.odooEditor.observerActive('dragAndDropMoveSnippet');
            gridUtils._resizeGrid(rowEl);
            this.options.wysiwyg.odooEditor.observerUnactive('dragAndDropMoveSnippet');
        } else if (this.$target[0].classList.contains('o_grid_item') && this.dropped) {
            // Case when dropping a grid item in a non-grid dropzone.
            this.options.wysiwyg.odooEditor.observerActive('dragAndDropMoveSnippet');
            gridUtils._convertToNormalColumn(this.$target[0]);
            this.options.wysiwyg.odooEditor.observerUnactive('dragAndDropMoveSnippet');
        }

        // TODO lot of this is duplicated code of the d&d feature of snippets
        if (!this.dropped) {
            let $el = $(closest(this.$body[0].querySelectorAll('.oe_drop_zone'), {x, y}));
            // Some drop zones might have been disabled.
            $el = $el.filter(this.$dropZones);
            if ($el.length) {
                $el.after(this.$target);
                // If the column is not dropped inside a dropzone.
                if ($el[0].classList.contains('oe_grid_zone')) {
                    // Case when a column is dropped near a grid.
                    const rowEl = $el[0].parentNode;

                    // If the column doesn't come from a snippet in grid mode,
                    // convert it.
                    if (!this.$target[0].classList.contains('o_grid_item')) {
                        this.options.wysiwyg.odooEditor.observerActive('dragAndDropMoveSnippet');
                        const spans = gridUtils._convertColumnToGrid(rowEl, this.$target[0], this.dragState.columnWidth, this.dragState.columnHeight);
                        this.options.wysiwyg.odooEditor.observerUnactive('dragAndDropMoveSnippet');
                        this.dragState.columnColCount = spans.columnColCount;
                        this.dragState.columnRowCount = spans.columnRowCount;
                    }

                    // Placing it in the top left corner.
                    this.options.wysiwyg.odooEditor.observerActive('dragAndDropMoveSnippet');
                    this.$target[0].style.gridArea = `1 / 1 / ${1 + this.dragState.columnRowCount} / ${1 + this.dragState.columnColCount}`;
                    const rowCount = Math.max(rowEl.dataset.rowCount, this.dragState.columnRowCount);
                    rowEl.dataset.rowCount = rowCount;
                    this.options.wysiwyg.odooEditor.observerUnactive('dragAndDropMoveSnippet');

                    // Setting the grid item z-index.
                    if (rowEl === this.dragState.startingGrid) {
                        this.$target[0].style.zIndex = this.dragState.startingZIndex;
                    } else {
                        gridUtils._setElementToMaxZindex(this.$target[0], rowEl);
                    }
                } else {
                    if (this.$target[0].classList.contains('o_grid_item')) {
                        // Case when a grid column is dropped near a non-grid
                        // dropzone.
                        this.options.wysiwyg.odooEditor.observerActive('dragAndDropMoveSnippet');
                        gridUtils._convertToNormalColumn(this.$target[0]);
                        this.options.wysiwyg.odooEditor.observerUnactive('dragAndDropMoveSnippet');
                    }
                }

                this.dropped = true;
            }
        }

        // Resize the grid from where the column came from (if any), as it may
        // have not been resized if the column did not go over it.
        if (this.dragState.startingGrid) {
            this.options.wysiwyg.odooEditor.observerActive('dragAndDropMoveSnippet');
            gridUtils._resizeGrid(this.dragState.startingGrid);
            this.options.wysiwyg.odooEditor.observerUnactive('dragAndDropMoveSnippet');
        }

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

            // If the target has a mobile order class, and if it was dropped in
            // another snippet, fill the gap left in the starting snippet.
            if (this.dragState.mobileOrder !== undefined
                && this.$target[0].parentNode !== this.dragState.startingParent) {
                ColumnLayoutMixin._fillRemovedItemGap(this.dragState.startingParent, this.dragState.mobileOrder);
            }

            this.$target.trigger('content_changed');
            $from.trigger('content_changed');
        }

        this.trigger_up('drag_and_drop_stop', {
            $snippet: this.$target,
        });
        const samePositionAsStart = this.$target[0].classList.contains('o_grid_item')
            ? (this.$target[0].parentNode === this.dragState.startingGrid
                && this.$target[0].style.gridArea === this.dragState.prevGridArea)
            : this._dropSiblings.prev === this.$target.prev()[0] && this._dropSiblings.next === this.$target.next()[0];
        if (!samePositionAsStart) {
            this.options.wysiwyg.odooEditor.historyStep();
        }

        this.dragState.restore();

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
            ev.data.optionNames.forEach((name) => {
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
        this.trigger_up('snippet_edition_request', {exec: this.removeSnippet.bind(this)});
    },
    /**
     * @private
     * @param {OdooEvent} ev
     */
    _onSnippetOptionVisibilityUpdate: function (ev) {
        if (this.options.wysiwyg.isSaving()) {
            // Do not update the option visibilities if we are destroying them.
            return;
        }
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
    _onDragMove({ x, y }) {
        if (!this.dragState.gridMode || !this.dragState.currentDropzoneEl) {
            return;
        }
        const columnEl = this.$target[0];
        const rowEl = columnEl.parentNode;

        // Computing the rowEl position.
        const rowElTop = rowEl.getBoundingClientRect().top;
        const rowElLeft = rowEl.getBoundingClientRect().left;

        // Getting the column dimensions.
        const borderWidth = parseFloat(window.getComputedStyle(columnEl).borderWidth);
        const columnHeight = columnEl.clientHeight + 2 * borderWidth;
        const columnWidth = columnEl.clientWidth + 2 * borderWidth;

        // Placing the column where the mouse is.
        let top = y - rowElTop - this.mousePositionYOnElement;
        const bottom = top + columnHeight;
        let left = x - rowElLeft - this.mousePositionXOnElement;

        // Horizontal and top overflow.
        left = clamp(left, 0, rowEl.clientWidth - columnWidth);
        top = top < 0 ? 0 : top;

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
        const dropzoneEl = this.dragState.currentDropzoneEl;
        const rowOverflow = Math.round((bottom - currentHeight) / (gridProp.rowSize + gridProp.rowGap));
        const updateRows = bottom > currentHeight || bottom <= currentHeight && bottom > startingHeight;
        const rowCount = Math.max(rowEl.dataset.rowCount, this.dragState.columnRowCount);
        const maxRowEnd = rowCount + gridUtils.additionalRowLimit + 1;
        if (Math.abs(rowOverflow) >= 1 && updateRows) {
            if (rowEnd <= maxRowEnd) {
                const dropzoneEnd = parseInt(dropzoneEl.style.gridRowEnd);
                dropzoneEl.style.gridRowEnd = dropzoneEnd + rowOverflow;
                backgroundGridEl.style.gridRowEnd = dropzoneEnd + rowOverflow;
                this.dragState.currentHeight += rowOverflow * (gridProp.rowSize + gridProp.rowGap);
            } else {
                // Don't add new rows if we have reached the limit.
                dropzoneEl.style.gridRowEnd = maxRowEnd;
                backgroundGridEl.style.gridRowEnd = maxRowEnd;
                this.dragState.currentHeight = (maxRowEnd - 1) * (gridProp.rowSize + gridProp.rowGap) - gridProp.rowGap;
            }
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
        'pointerdown': '_onMouseDown',
        'pointerup': '_onMouseUp',
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
        "clean_ui_request": "_onCleanUIRequest",
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
        "update_invisible_dom": "_onUpdateInvisibleDom",
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

        this._mutex = new Mutex();

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
            '.o_datetime_picker',
        ].join(', ');

        this.loadingTimers = {};
        this.loadingElements = {};
        this._loadingEffectDisabled = false;
        this._onClick = this._onClick.bind(this);

        this.orm = this.bindService("orm");
        this.notification = this.bindService("notification");
        this.dialog = this.bindService("dialog");
    },
    /**
     * @override
     */
    willStart: function () {
        // Preload colorpalette dependencies without waiting for them. The
        // widget have huge chances of being used by the user (clicking on any
        // text will load it). The colorpalette itself will do the actual
        // waiting of the loading completion.
        this.options.wysiwyg.getColorpickerTemplate();
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

        // TODO somehow this attribute is not on the HTML element of the backend
        // ... it probably should be.
        const context = this.options.context || session.user_context || {};
        const userLang = context.user_lang || context.lang || 'en_US';
        this.el.setAttribute('lang', pyToJsLocale(userLang));

        // We need to activate the touch events to be able to drag and drop
        // snippets on devices with a touch screen.
        this.__onTouchEvent = this._onTouchEvent.bind(this);
        document.addEventListener("touchstart", this.__onTouchEvent, true);
        document.addEventListener("touchmove", this.__onTouchEvent, true);
        document.addEventListener("touchend", this.__onTouchEvent, true);

        this.customizePanel = document.createElement('div');
        this.customizePanel.classList.add('o_we_customize_panel', 'd-none');

        this._toolbarWrapperEl = document.createElement('div');
        this._toolbarWrapperEl.classList.add('o_we_toolbar_wrapper');
        class WebsiteToolbar extends Component {
            static components = { Toolbar, LinkTools };
            static template = xml`
                <Toolbar t-props="props.wysiwygState.toolbarProps">
                    <t t-if="props.wysiwygState.linkToolProps">
                        <LinkTools t-props="props.wysiwygState.linkToolProps" />
                    </t>
                </Toolbar>
            `;
            static props = {
                wysiwygState: Object,
            };
        }
        // Add the toolbarWrapperEl to the dom for owl to properly mount the
        // Toolbar.
        document.body.append(this._toolbarWrapperEl);
        this._toolbarWrapperEl.style.display = 'none';
        await attachComponent(this, this._toolbarWrapperEl, WebsiteToolbar, {
            wysiwygState: this.options.wysiwyg.state,
        });
        this._toolbarWrapperEl.style.display = 'contents';

        const toolbarEl = this._toolbarWrapperEl.firstChild;
        toolbarEl.classList.remove('oe-floating');
        this.options.wysiwyg.toolbarEl.classList.add('d-none');
        this.options.wysiwyg.setupToolbar(toolbarEl);
        this._addToolbar();
        this._checkEditorToolbarVisibilityCallback = this._checkEditorToolbarVisibility.bind(this);
        $(this.options.wysiwyg.odooEditor.document.body).on('click', this._checkEditorToolbarVisibilityCallback);

        this.invisibleDOMPanelEl = document.createElement('div');
        this.invisibleDOMPanelEl.classList.add('o_we_invisible_el_panel');
        this.invisibleDOMPanelEl.appendChild(
            $('<div/>', {
                text: _t('Invisible Elements'),
                class: 'o_panel_header',
            })[0]
        );

        // Prepare snippets editor environment
        this.$snippetEditorArea = $('<div/>', {
            id: 'oe_manipulators',
        });
        this.$body.prepend(this.$snippetEditorArea);
        this.options.getDragAndDropOptions = this._getDragAndDropOptions.bind(this);

        // Add tooltips on we-title elements whose text overflows and on all
        // elements with available tooltip text. Note that the tooltips of the
        // blocks should not be taken into account here because they have
        // tooltips with a particular behavior (see _showSnippetTooltip).
        this.tooltips = new Tooltip(this.el, {
            selector: 'we-title, [title]:not(.oe_snippet)',
            placement: 'bottom',
            delay: 100,
            // Ensure the tooltips have a good position when in iframe.
            container: this.el,
            // Prevent horizontal scroll when tooltip is displayed.
            boundary: this.el.ownerDocument.body,
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

        // Active snippet editor on click in the page
        this.$document.on('click.snippets_menu', '*', this._onClick);
        // Needed as bootstrap stop the propagation of click events for dropdowns
        this.$document.on('mouseup.snippets_menu', '.dropdown-toggle', this._onClick);

        // Adapt overlay covering when the window is resized / content changes
        this.debouncedCoverUpdate = throttleForAnimation(() => {
            this.updateCurrentSnippetEditorOverlay();
        });
        this.$window.on("resize.snippets_menu", this.debouncedCoverUpdate);
        this.$body.on("content_changed.snippets_menu", this.debouncedCoverUpdate);
        $(this.$body[0].ownerDocument.defaultView).on(
            "resize.snippets_menu",
            this.debouncedCoverUpdate
        );

        // On keydown add a class on the active overlay to hide it and show it
        // again when the mouse moves
        this.$body.on('keydown.snippets_menu', () => {
            this.__overlayKeyWasDown = true;
            this.snippetEditors.forEach(editor => {
                editor.toggleOverlayVisibility(false);
            });
        });
        this.$body.on('mousemove.snippets_menu, mousedown.snippets_menu', throttleForAnimation(() => {
            if (!this.__overlayKeyWasDown) {
                return;
            }
            this.__overlayKeyWasDown = false;
            this.snippetEditors.forEach(editor => {
                editor.toggleOverlayVisibility(true);
                editor.cover();
            });
        }));

        // Hide the active overlay when scrolling.
        // Show it again and recompute all the overlays after the scroll.
        this.$scrollingElement = $().getScrollingElement(this.$body[0].ownerDocument);
        if (!this.$scrollingElement[0]) {
            this.$scrollingElement = $(this.ownerDocument).find('.o_editable');
        }
        this.$scrollingTarget = $().getScrollingTarget(this.$scrollingElement);
        this._onScrollingElementScroll = throttleForAnimation(() => {
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
        });
        // We use addEventListener instead of jQuery because we need 'capture'.
        // Setting capture to true allows to take advantage of event bubbling
        // for events that otherwise don’t support it. (e.g. useful when
        // scrolling a modal)
        this.$scrollingTarget[0].addEventListener('scroll', this._onScrollingElementScroll, {capture: true});

        if (this.options.enableTranslation) {
            // Load the sidebar with the style tab only.
            await this._loadSnippetsTemplates();
            defs.push(this._updateInvisibleDOM());
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
            return Promise.all(defs).then(() => {});
        }

        this.emptyOptionsTabContent = document.createElement('div');
        this.emptyOptionsTabContent.classList.add('text-center', 'pt-5');
        this.emptyOptionsTabContent.append(_t("Select a block on your page to style it."));

        // Fetch snippet templates and compute it
        defs.push((async () => {
            await this._loadSnippetsTemplates(this.options.invalidateSnippetCache);
            await this._updateInvisibleDOM();
        })());

        // Auto-selects text elements with a specific class and remove this
        // on text changes
        const alreadySelectedElements = new Set();
        this.$body.on('click.snippets_menu', '.o_default_snippet_text', ev => {
            const el = ev.currentTarget;
            if (alreadySelectedElements.has(el)) {
                // If the element was already selected in such a way before, we
                // don't reselect it. This actually allows to have the first
                // click on an element to select its text, but the second click
                // to place the cursor inside of that text.
                return;
            }
            alreadySelectedElements.add(el);
            $(el).selectContent();
        });
        this.$body.on('keyup.snippets_menu', () => {
            // Note: we cannot listen to keyup in .o_default_snippet_text
            // elements via delegation because keyup only bubbles from focusable
            // elements which contenteditable are not.
            const selection = this.$body[0].ownerDocument.getSelection();
            if (!selection.rangeCount) {
                return;
            }
            const range = selection.getRangeAt(0);
            const $defaultTextEl = $(range.startContainer).closest('.o_default_snippet_text');
            $defaultTextEl.removeClass('o_default_snippet_text');
            alreadySelectedElements.delete($defaultTextEl[0]);
        });
        const refreshSnippetEditors = debounce(() => {
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
            }

            // Trigger a resize event once entering edit mode as the snippets
            // menu will take part of the screen width (delayed because of
            // animation). (TODO wait for real animation end)
            setTimeout(() => {
                this.$window[0].dispatchEvent(new Event("resize"));
            }, 1000);
        });
    },
    /**
     * @override
     */
    destroy: function () {
        this._super.apply(this, arguments);
        // Remove listeners for touch events.
        document.removeEventListener("touchstart", this.__onTouchEvent, true);
        document.removeEventListener("touchmove", this.__onTouchEvent, true);
        document.removeEventListener("touchend", this.__onTouchEvent, true);
        this.draggableComponent && this.draggableComponent.destroy();
        if (this.$window) {
            if (this.$snippetEditorArea) {
                this.$snippetEditorArea.remove();
            }
            this.$window.off('.snippets_menu');
            this.$document.off('.snippets_menu');

            if (this.$scrollingTarget) {
                this.$scrollingTarget[0].removeEventListener('scroll', this._onScrollingElementScroll, {capture: true});
            }
        }
        if (this.debouncedCoverUpdate) {
            this.debouncedCoverUpdate.cancel();
        }
        $(document.body).off('click', this._checkEditorToolbarVisibilityCallback);
        this.el.ownerDocument.body.classList.remove('editor_has_snippets');
        // Dispose BS tooltips.
        this.tooltips.dispose();
        options.clearServiceCache();
        options.clearControlledSnippets();
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
        // Wait for snippet post-drop code here, since sometimes we save very
        // quickly after a snippet drop during automated testing, which breaks
        // some options code (executed while destroying the editor).
        // TODO we should find a better way, by better locking the drag and drop
        // code inside the edition mutex... which unfortunately cannot be done
        // given the state of the code, as internal operations of that drag and
        // drop code need to use the mutex themselves.
        await this.postSnippetDropPromise;

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
        [...this.getEditableArea()].forEach(editableAreaEl => {
            editableAreaEl.querySelectorAll("[data-visibility='conditional']")
                            .forEach(invisibleEl => delete invisibleEl.dataset.invisible);
        });
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
        let context = Object.assign({}, this.options.context);
        if (context.user_lang) {
            context.lang = this.options.context.user_lang;
            context.snippet_lang = this.options.context.lang;
        }
        this._defLoadSnippets = this.orm.silent.call(
            "ir.ui.view",
            "render_public_asset",
            [this.options.snippets, {}],
            { context }
        );
        cacheSnippetTemplate[this.options.snippets] = this._defLoadSnippets;
        return this._defLoadSnippets;
    },
    /**
     * Visually hide or display this snippet menu
     * @param {boolean} foldState
     */
    setFolded: function (foldState = true) {
        this.el.classList.toggle('d-none', foldState);
        this.el.ownerDocument.body.classList.toggle('editor_has_snippets', !foldState);
        this.folded = !!foldState;
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
                const selection = this.$body[0].ownerDocument.getSelection();
                const range = selection?.rangeCount && selection.getRangeAt(0);
                const currentlySelectedNode = range?.commonAncestorContainer;
                // In some cases (e.g. in translation mode) it's possible to have
                // all snippet editors destroyed after disabling text options.
                // We still want to keep the toolbar available in this case.
                const isEditableTextElementSelected =
                    currentlySelectedNode?.nodeType === Node.TEXT_NODE &&
                    !!currentlySelectedNode?.parentNode?.isContentEditable;
                if (!isEditableTextElementSelected) {
                    this._activateEmptyOptionsTab();
                }
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
        this.postSnippetDropPromise = new Promise(resolve => {
            this._postSnippetDropResolver = resolve;
        });

        // First call the onBuilt of all options of each item in the snippet
        // (and so build their editor instance first).
        await this._callForEachChildSnippet($target, function (editor, $snippet) {
            return editor.buildSnippet($target[0]);
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

        if (this.__postSnippetDropExtraActions) {
            this.__postSnippetDropExtraActions();
            delete this.__postSnippetDropExtraActions;
        }
        this._postSnippetDropResolver();
    },
    /**
     * Public implementation of _execWithLoadingEffect.
     *
     * @see this._execWithLoadingEffect for parameters
     */
    execWithLoadingEffect(action, contentLoading = true, delay = 500) {
        return this._execWithLoadingEffect(...arguments);
    },
    reload_snippet_dropzones() {
        this._disableUndroppableSnippets();
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
     * @param {Boolean} [toInsertInline=false]
     *        elements which are inline as the "s_badge" snippet for example
     * @param {Object} [selectorGrids = []]
     *        elements which are in grid mode and for which a grid dropzone
     *        needs to be inserted
     */
    _activateInsertionZones($selectorSiblings, $selectorChildren, canBeSanitizedUnless, toInsertInline, selectorGrids = [], fromIframe = false) {
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
            selectorGrids = new Set([...selectorGrids].filter(rowEl => $open[0].contains(rowEl)));
        }

        // Check if the drop zone should be horizontal or vertical
        function setDropZoneDirection($elem, $parent, toInsertInline, $sibling) {
            let vertical = false;
            let style = {};
            $sibling = $sibling || $elem;
            const css = window.getComputedStyle($elem[0]);
            const parentCss = window.getComputedStyle($parent[0]);
            const float = css.float || css.cssFloat;
            const display = parentCss.display;
            const flex = parentCss.flexDirection;
            if (toInsertInline || float === 'left' || float === 'right' || (display === 'flex' && flex === 'row')) {
                if (!toInsertInline) {
                    style['float'] = float;
                }
                if ((parseInt($sibling.parent().width()) !== parseInt($sibling.outerWidth(true)))) {
                    vertical = true;
                    style['height'] = Math.max($sibling.outerHeight(), 30) + 'px';
                    if (toInsertInline) {
                        style["display"] = "inline-block";
                        style["verticalAlign"] = "middle";
                        style["float"] = "none";
                    }
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
        if ($clone.length && !$clone[0].parentElement.classList.contains("o_grid_mode")) {
            var $neighbor = $clone.prev();
            if (!$neighbor.length) {
                $neighbor = $clone.next();
            }
            var data;
            if ($neighbor.length) {
                data = setDropZoneDirection($neighbor, $neighbor.parent(), toInsertInline);
            } else {
                data = {
                    vertical: false,
                    style: {},
                };
            }
            self._insertDropzone($('<we-hook/>').insertAfter($clone), data.vertical, data.style, canBeSanitizedUnless);
        }
        // If a modal or a dropdown is open, add the grid of the clone in the
        // grid selectors to still be able to drop where the drag started.
        if ($clone.length && $open.length && $clone[0].parentElement.classList.contains("o_grid_mode")) {
            selectorGrids.add($clone[0].parentElement);
        }

        if ($selectorChildren) {
            $selectorChildren.each(function () {
                var data;
                var $zone = $(this);
                var $children = $zone.find('> :not(.oe_drop_zone, .oe_drop_clone)');

                if (!$zone.children().last().is('.oe_drop_zone')) {
                    data = testPreviousSibling($zone[0].lastChild, $zone)
                        || setDropZoneDirection($zone, $zone, toInsertInline, $children.last());
                    self._insertDropzone($('<we-hook/>').appendTo($zone), data.vertical, data.style, canBeSanitizedUnless);
                }

                if (!$zone.children().first().is('.oe_drop_clone')) {
                    data = testPreviousSibling($zone[0].firstChild, $zone)
                        || setDropZoneDirection($zone, $zone, toInsertInline, $children.first());
                    self._insertDropzone($('<we-hook/>').prependTo($zone), data.vertical, data.style, canBeSanitizedUnless);
                }
            });

            // add children near drop zone
            $selectorSiblings = $(unique(($selectorSiblings || $()).add($selectorChildren.children()).get()));
        }

        const noDropZonesSelector = '.o_we_no_overlay, :not(:visible)';
        if ($selectorSiblings) {
            $selectorSiblings.not(`.oe_drop_zone, .oe_drop_clone, ${noDropZonesSelector}`).each(function () {
                var data;
                var $zone = $(this);
                var $zoneToCheck = $zone;

                while ($zoneToCheck.prev(noDropZonesSelector).length) {
                    $zoneToCheck = $zoneToCheck.prev();
                }
                if (!$zoneToCheck.prev('.oe_drop_zone:visible, .oe_drop_clone').length) {
                    data = setDropZoneDirection($zone, $zone.parent(), toInsertInline);
                    self._insertDropzone($('<we-hook/>').insertBefore($zone), data.vertical, data.style, canBeSanitizedUnless);
                }

                $zoneToCheck = $zone;
                while ($zoneToCheck.next(noDropZonesSelector).length) {
                    $zoneToCheck = $zoneToCheck.next();
                }
                if (!$zoneToCheck.next('.oe_drop_zone:visible, .oe_drop_clone').length) {
                    data = setDropZoneDirection($zone, $zone.parent(), toInsertInline);
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
        if (bodyWindow.frameElement && bodyWindow !== this.ownerDocument.defaultView && !fromIframe) {
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
            const isMobile = this._isMobile();
            const invisibleSelector = `.o_snippet_invisible, ${isMobile ? '.o_snippet_mobile_invisible' : '.o_snippet_desktop_invisible'}`;
            const $selector = this.options.enableTranslation ? this.$body : globalSelector.all();
            let $invisibleSnippets = $selector.find(invisibleSelector).addBack(invisibleSelector);

            if (this.options.enableTranslation) {
                // In translate mode, we do not want to be able to activate a
                // hidden header or footer.
                $invisibleSnippets = $invisibleSnippets.not("header, footer");
            }
            $invisibleDOMPanelEl.toggleClass('d-none', !$invisibleSnippets.length);

            // descendantPerSnippet: a map with its keys set to invisible
            // snippets that have invisible descendants. The value corresponding
            // to an invisible snippet element is a list filled with all its
            // descendant invisible snippets except those that have a closer
            // invisible snippet ancestor.
            const descendantPerSnippet = new Map();
            // Filter the "$invisibleSnippets" to only keep the root snippets
            // and create the map ("descendantPerSnippet") of the snippets and
            // their descendant snippets.
            const rootInvisibleSnippetEls = [...$invisibleSnippets].filter(invisibleSnippetEl => {
                const ancestorInvisibleEl = invisibleSnippetEl
                                                 .parentElement.closest(invisibleSelector);
                if (!ancestorInvisibleEl) {
                    return true;
                }
                const descendantSnippets = descendantPerSnippet.get(ancestorInvisibleEl) || [];
                descendantPerSnippet.set(ancestorInvisibleEl,
                    [...descendantSnippets, invisibleSnippetEl]);
                return false;
            });
            // Insert an invisible snippet in its "parentEl" element.
            const createInvisibleElement = async (invisibleSnippetEl, isRootParent, isDescendant,
                                                  parentEl) => {
                const $invisibleSnippetEl = $(invisibleSnippetEl);
                $invisibleSnippetEl.__force_create_editor = true;
                const editor = await this._createSnippetEditor($invisibleSnippetEl);
                const invisibleEntryEl = document.createElement("div");
                invisibleEntryEl.className = `${isRootParent ? "o_we_invisible_root_parent" : ""}`;
                invisibleEntryEl.classList.add("o_we_invisible_entry", "d-flex",
                    "align-items-center", "justify-content-between");
                invisibleEntryEl.classList.toggle("o_we_sublevel_1", isDescendant);
                const titleEl = document.createElement("we-title");
                titleEl.textContent = editor.getName();
                invisibleEntryEl.appendChild(titleEl);
                const iconEl = document.createElement("i");
                const eyeIconClass = editor.isTargetVisible() ? "fa-eye" : "fa-eye-slash";
                iconEl.classList.add("fa", "ms-2", eyeIconClass);
                invisibleEntryEl.appendChild(iconEl);
                parentEl.appendChild(invisibleEntryEl);
                this.invisibleDOMMap.set(invisibleEntryEl, invisibleSnippetEl);
            };
            // Insert all the invisible snippets contained in "snippetEls" as
            // well as their descendants in the "parentEl" element. If
            // "snippetEls" is set to "rootInvisibleSnippetEls" and "parentEl"
            // is set to "$invisibleDOMPanelEl[0]", then fills the right
            // invisible panel like this:
            // rootInvisibleSnippet
            //     └ descendantInvisibleSnippet
            //          └ descendantOfDescendantInvisibleSnippet
            //               └ etc...
            const createInvisibleElements = async (snippetEls, isDescendant, parentEl) => {
                for (const snippetEl of snippetEls) {
                    const descendantSnippetEls = descendantPerSnippet.get(snippetEl);
                    // An element is considered as "RootParent" if it has one or
                    // more invisible descendants but is not a descendant.
                    await createInvisibleElement(snippetEl,
                        !isDescendant && !!descendantSnippetEls, isDescendant, parentEl);
                    if (descendantSnippetEls) {
                        // Insert all the descendant snippets in a list.
                        const listEntryEl = document.createElement("ul");
                        await createInvisibleElements(descendantSnippetEls, true, listEntryEl);
                        parentEl.appendChild(listEntryEl);
                    }
                }
            };
            return createInvisibleElements(rootInvisibleSnippetEls, false, $invisibleDOMPanelEl[0]);
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
        if (this.options.enableTranslation && $snippet && !this._allowInTranslationMode($snippet)) {
            // In translate mode, only activate allowed snippets (e.g., even if
            // we create editors for invisible elements when translating them,
            // we only want to toggle their visibility when the related sidebar
            // buttons are clicked).
            const translationEditors = this.snippetEditors.filter(editor => {
                return this._allowInTranslationMode(editor.$target);
            });
            // Before returning, we need to clean editors if their snippets are
            // allowed in the translation mode.
            for (const editor of translationEditors) {
                await editor.cleanForSave();
                editor.destroy();
            }
            return;
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
                        }
                    }
                }

                if (!previewMode) {
                    // As some options can only be generated using JavaScript
                    // (e.g. 'SwitchableViews'), it may happen at this point
                    // that the overlay is activated even though there are no
                    // options. That's why we disable the overlay if there are
                    // no options to enable.
                    if (editorToEnable && !customize$Elements) {
                        editorToEnable.toggleOverlay(false);
                    }
                    this._updateRightPanelContent({
                        content: customize$Elements || [],
                        tab: customize$Elements ? this.tabs.OPTIONS : this.tabs.BLOCKS,
                    });
                }

                return editorToEnable;
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
        var defs = Array.from($snippet.add(globalSelector.all($snippet))).map((el) => {
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

        // TODO in master: FOR_DROP should be a param of the function.
        const forDropID = 'FOR_DROP';
        const forDrop = exclude && exclude.startsWith(forDropID);
        if (forDrop) {
            exclude = exclude.substring(forDropID.length);
        }

        // The `:not(.o_editable_media)` part is handled outside of the selector
        // (see filterFunc).
        // Note: the `:not([contenteditable="true"])` part was there for that
        // same purpose before the implementation of the o_editable_media class.
        // It still make sense for potential editable areas though. Although it
        // should be reviewed if we are to handle more hierarchy of nodes being
        // editable despite their non editable environment.
        // Without the `:not(.s_social_media)`, it is no longer possible to edit
        // icons in the social media snippet. This should be fixed in a more
        // proper way to get rid of this hack.
        exclude += `${exclude && ', '}.o_snippet_not_selectable`;

        let filterFunc = function () {
            // Exclude what it is asked to exclude.
            if ($(this).is(exclude)) {
                return false;
            }
            if (noCheck) {
                // When noCheck is true, we only check the exclude.
                return true;
            }
            // `o_editable_media` bypasses the `o_not_editable` class except for
            // drag & drop.
            if (!forDrop && this.classList.contains('o_editable_media')) {
                return weUtils.shouldEditableMediaBeEditable(this);
            }
            if (forDrop && !isChildren) {
                // it's a drop-in.
                return !$(this)
                    .is('.o_not_editable :not([contenteditable="true"]), .o_not_editable');
            }
            if (isChildren) {
                return !$(this).is('.o_not_editable *');
            }
            return !$(this)
                .is('.o_not_editable:not(.s_social_media) :not([contenteditable="true"])');
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
        // In translate mode, it is only possible to modify text content but not
        // the structure of the snippets. For this reason, the "Editable area"
        // are only the text zones and they should not be used inside functions
        // such as "is", "closest" and "all".
        if (noCheck || this.options.enableTranslation) {
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
        this._patchForComputeSnippetTemplates($html);
        var $scroll = $html.siblings('#o_scroll');

        // TODO adapt in master. This patches the BlogPostTagSelection option
        // in stable versions. Done here to avoid converting the html back to
        // a string.
        const optionEl = $html.find('[data-js="BlogPostTagSelection"][data-selector=".o_wblog_post_page_cover"]')[0];
        if (optionEl) {
            optionEl.dataset.selector = '.o_wblog_post_page_cover[data-res-model="blog.post"]';
        }

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
            // Note that the optionID will be used to add a class
            // `snippet-option-XXX` (XXX being the optionID) on the related
            // option DOM. This is used in JS tours. The data-js attribute can
            // be used without a corresponding JS class being defined.
            const optionID = $style.data('js');
            var option = {
                'option': optionID,
                'base_selector': selector,
                'base_exclude': exclude,
                'base_target': target,
                'selector': self._computeSelectorFunctions(selector, exclude, target, noCheck),
                '$el': $style,
                'drop-near': $style.data('drop-near') && self._computeSelectorFunctions($style.data('drop-near'), 'FOR_DROP', false, noCheck, true, excludeParent),
                'drop-in': $style.data('drop-in') && self._computeSelectorFunctions($style.data('drop-in'), 'FOR_DROP', false, noCheck),
                'drop-exclude-ancestor': this.dataset.dropExcludeAncestor,
                'drop-lock-within': this.dataset.dropLockWithin,
                'data': Object.assign({string: $style.attr('string')}, $style.data()),
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
        globalSelector.is = function ($from, options = {}) {
            for (var i = 0, len = selectors.length; i < len; i++) {
                if (options.onlyTextOptions ? $from.is(self.templateOptions[i].data.textSelector) : selectors[i].is($from)) {
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
                const thumbnailSrc = escape(el.dataset.oeThumbnail);
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
                        <div class="oe_snippet_thumbnail_img" style="background-image: url(${thumbnailSrc});"></div>
                        <span class="oe_snippet_thumbnail_title">${escape(name)}</span>
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
                    btnRenameEl.title = _t("Rename %s", name);
                    $snippet.append(btnRenameEl);
                    const btnEl = document.createElement('we-button');
                    btnEl.dataset.snippetId = $snippet.data('oeSnippetId');
                    btnEl.classList.add('o_delete_btn', 'fa', 'fa-trash', 'btn', 'o_we_hover_danger');
                    btnEl.title = _t("Delete %s", name);
                    $snippet.append(btnEl);
                }
            })
            .not('[data-module-id]');

        // Enable the snippet tooltips
        this.$snippets.tooltip({
            trigger: 'manual',
            placement: 'bottom',
            title: _t("Drag and drop the building block."),
            // Ensure the tooltips have a good position when in iframe.
            container: this.el,
            // Prevent horizontal scroll when tooltip is displayed.
            boundary: this.el.ownerDocument.body,
        });

        // Hide scroll if no snippets defined
        if (!this.$snippets.length) {
            this.$el.detach();
        }

        // Register the text nodes that needs to be auto-selected on click
        this._registerDefaultTexts();

        // Add the computed template and make elements draggable
        this.$el.html($html);
        this.$el.append(this.customizePanel);
        this.$el.append(this.invisibleDOMPanelEl);
        this._makeSnippetDraggable();
        this._disableUndroppableSnippets();

        this.$el.addClass('o_loaded');
        $(this.el.ownerDocument.body).toggleClass('editor_has_snippets', !this.folded);
    },
    /**
     * Eases patching the XML definition for snippets and options in stable
     * versions. Note: in the future, we will probably move to other ways to
     * define snippets and options.
     *
     * @private
     * @param {jQuery}
     */
    _patchForComputeSnippetTemplates($html) {
        // TODO: Remove in master and add it back in the template.
        const $vAlignOption = $html.find("#row_valign_snippet_option");
        $vAlignOption[0].dataset.js = "vAlignment";
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

        // In translate mode, only allow creating the editor if the target is a
        // text option snippet.
        if (!$snippet.__force_create_editor && this.options.enableTranslation && !this._allowInTranslationMode($snippet)) {
            return Promise.resolve(null);
        }
        // TODO: Adapt in master (property used in stable for compatibility).
        delete $snippet.__force_create_editor;

        var def;
        if (this._allowParentsEditors($snippet)) {
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
            const checkSanitize = isSanitizeForbidden === "form"
                ? (el) => !el.closest('[data-oe-sanitize]:not([data-oe-sanitize="allow_form"])')
                : isSanitizeForbidden
                    ? (el) => !el.closest('[data-oe-sanitize]')
                    : () => true;
            const isVisible = (el) => el.closest(".o_snippet_invisible")
                ? !(el.offsetHeight === 0 || el.offsetWidth === 0)
                : true;
            const canDrop = ($els) => [...$els].some((el) => checkSanitize(el) && isVisible(el));

            var check = false;
            self.templateOptions.forEach((option, k) => {
                if (check || !($snippetBody.is(option.base_selector) && !$snippetBody.is(option.base_exclude))) {
                    return;
                }

                k = isSanitizeForbidden ? 'forbidden/' + k : k;
                cache[k] = cache[k] || {
                    'drop-near': option['drop-near'] ? canDrop(option['drop-near'].all()) : false,
                    'drop-in': option['drop-in'] ? canDrop(option['drop-in'].all()) : false,
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
    _getDragAndDropOptions(options = {}) {
        let iframeWindow = false;
        if (this.$body[0].ownerDocument.defaultView !== window) {
            iframeWindow = this.$body[0].ownerDocument.defaultView;
        }
        return Object.assign({}, options, {
            iframeWindow,
            cursor: "move",
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
        const skip = $hook.closest('[data-oe-sanitize="no_block"]').length;
        let forbidSanitize;
        if (canBeSanitizedUnless === 'form') {
            forbidSanitize = $hook.closest('[data-oe-sanitize]:not([data-oe-sanitize="allow_form"]):not([data-oe-sanitize="no_block"])').length;
        } else {
            forbidSanitize = !canBeSanitizedUnless && $hook.closest('[data-oe-sanitize]:not([data-oe-sanitize="no_block"])').length;
        }
        var $dropzone = $('<div/>', {
            'class': skip ? 'd-none' : 'oe_drop_zone oe_insert' + (vertical ? ' oe_vertical' : '') +
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
     */
    _makeSnippetDraggable() {
        if (this.draggableComponent) {
            this.draggableComponent.destroy();
        }
        var $toInsert, dropped, $snippet;
        let $dropZones;

        let dragAndDropResolve;
        let $scrollingElement = $().getScrollingElement(this.$body[0].ownerDocument);
        if (!$scrollingElement[0] || $scrollingElement.find('body.o_in_iframe').length) {
            $scrollingElement = $(this.ownerDocument).find('.o_editable');
        }

        const dragAndDropOptions = this.options.getDragAndDropOptions({
            el: this.$el[0],
            elements: ".oe_snippet",
            scrollingElement: $scrollingElement[0],
            handle: '.oe_snippet_thumbnail:not(.o_we_already_dragging)',
            cancel: '.oe_snippet.o_disabled',
            dropzones: () => {
                return $dropZones.toArray();
            },
            helper: ({ element, elementRect, helperOffset, x, y }) => {
                const dragSnip = element.cloneNode(true);
                dragSnip.querySelectorAll('.o_delete_btn, .o_rename_btn').forEach(
                    el => el.remove()
                );
                dragSnip.style.position = "fixed";
                this.$el[0].ownerDocument.body.append(dragSnip);
                // Prepare the offset of the helper to be at the position it was dragged from
                helperOffset.x = x - elementRect.x;
                helperOffset.y = y - elementRect.y;
                return dragSnip;
            },
            onDragStart: ({ element }) => {
                this._hideSnippetTooltips();

                const prom = new Promise(resolve => dragAndDropResolve = () => resolve());
                this._mutex.exec(() => prom);

                const doc = this.options.wysiwyg.odooEditor.document;
                $(doc.body).addClass('oe_dropzone_active');

                this.options.wysiwyg.odooEditor.automaticStepUnactive();

                this.$el.find('.oe_snippet_thumbnail').addClass('o_we_already_dragging');
                this.options.wysiwyg.odooEditor.observerUnactive('dragAndDropCreateSnippet');

                dropped = false;
                $snippet = $(element);
                var $baseBody = $snippet.find('.oe_snippet_body');
                var $selectorSiblings = $();
                var $selectorChildren = $();
                const selectorExcludeAncestor = [];
                var temp = this.templateOptions;
                for (var k in temp) {
                    if ($baseBody.is(temp[k].base_selector) && !$baseBody.is(temp[k].base_exclude)) {
                        if (temp[k]['drop-near']) {
                            $selectorSiblings = $selectorSiblings.add(temp[k]['drop-near'].all());
                        }
                        if (temp[k]['drop-in']) {
                            $selectorChildren = $selectorChildren.add(temp[k]['drop-in'].all());
                        }
                        if (temp[k]['drop-exclude-ancestor']) {
                            selectorExcludeAncestor.push(temp[k]['drop-exclude-ancestor']);
                        }
                    }
                }

                // Prevent dropping an element into another one.
                // (E.g. ToC inside another ToC)
                for (const excludedAncestorSelector of selectorExcludeAncestor) {
                    $selectorSiblings = $selectorSiblings.filter((i, el) => !el.closest(excludedAncestorSelector));
                    $selectorChildren = $selectorChildren.filter((i, el) => !el.closest(excludedAncestorSelector));
                }

                $toInsert = $baseBody.clone();
                // Color-customize dynamic SVGs in dropped snippets with current theme colors.
                [...$toInsert.find('img[src^="/web_editor/shape/"]')].forEach(dynamicSvg => {
                    const colorCustomizedURL = new URL(dynamicSvg.getAttribute('src'), window.location.origin);
                    colorCustomizedURL.searchParams.forEach((value, key) => {
                        const match = key.match(/^c([1-5])$/);
                        if (match) {
                            colorCustomizedURL.searchParams.set(key, weUtils.getCSSVariableValue(`o-color-${match[1]}`));
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
                // Specific case for inline snippet (e.g. "s_badge")
                    $baseBody[0].classList.remove("oe_snippet_body");
                    const toInsertInline = window.getComputedStyle($baseBody[0]).display.includes('inline');
                    $baseBody[0].classList.add("oe_snippet_body");
                    this._activateInsertionZones($selectorSiblings, $selectorChildren, canBeSanitizedUnless, toInsertInline);
                $dropZones = this.getEditableArea().find('.oe_drop_zone');
                if (forbidSanitize === 'form') {
                    $dropZones = $dropZones.filter((i, el) => !el.closest('[data-oe-sanitize]:not([data-oe-sanitize="allow_form"]) .oe_drop_zone'));
                } else if (forbidSanitize) {
                    $dropZones = $dropZones.filter((i, el) => !el.closest('[data-oe-sanitize] .oe_drop_zone'));
                }
                // If a modal is open, the scroll target must be that modal
                const $openModal = this.getEditableArea().find('.modal:visible');
                if ($openModal.length) {
                    this.draggableComponent.update({ scrollingElement: $openModal[0]});
                    $scrollingElement = $openModal;
                }
                this.trigger_up('drop_zone_start');
            },
            dropzoneOver: ({ dropzone }) => {
                if (dropped) {
                    $toInsert.detach();
                    $toInsert.addClass('oe_snippet_body');
                    [...$dropZones].forEach(dropzoneEl =>
                        dropzoneEl.classList.remove("invisible"));
                }
                dropped = true;
                $(dropzone.el).first().after($toInsert).addClass('invisible');
                $toInsert.removeClass('oe_snippet_body');
                this.trigger_up('drop_zone_over');
            },
            dropzoneOut: ({ dropzone }) => {
                var prev = $toInsert.prev();
                if (dropzone.el === prev[0]) {
                    dropped = false;
                    $toInsert.detach();
                    $(dropzone.el).removeClass('invisible');
                    $toInsert.addClass('oe_snippet_body');
                }
                this.trigger_up('drop_zone_out');
            },
            onDragEnd: async ({ x, y, helper }) => {
                const doc = this.options.wysiwyg.odooEditor.document;
                $(doc.body).removeClass('oe_dropzone_active');
                this.options.wysiwyg.odooEditor.automaticStepUnactive();
                this.options.wysiwyg.odooEditor.automaticStepSkipStack();
                $toInsert.removeClass('oe_snippet_body');
                $scrollingElement.off('scroll.scrolling_element');
                if (!dropped && y > 3 && x + helper.getBoundingClientRect().height < this.el.getBoundingClientRect().left) {
                    const point = { x, y };
                    let droppedOnNotNearest = touching(doc.body.querySelectorAll('.oe_structure_not_nearest'), point);
                    // If dropped outside of a dropzone with class oe_structure_not_nearest,
                    // move the snippet to the nearest dropzone without it
                    const selector = droppedOnNotNearest
                        ? '.oe_drop_zone'
                        : ':not(.oe_structure_not_nearest) > .oe_drop_zone';
                    let $el = $(closest(doc.body.querySelectorAll(selector), point));
                    // Some drop zones might have been disabled.
                    $el = $el.filter($dropZones);
                    if ($el.length) {
                        $el.after($toInsert);
                        dropped = true;
                    }
                }

                this.getEditableArea().find('.oe_drop_zone').remove();

                let $toInsertParent;
                let prev;
                let next;
                if (dropped) {
                    prev = $toInsert.first()[0].previousSibling;
                    next = $toInsert.last()[0].nextSibling;

                    $toInsertParent = $toInsert.parent();
                    $toInsert.detach();
                }

                this.options.wysiwyg.odooEditor.observerActive('dragAndDropCreateSnippet');

                if (dropped) {
                    if (prev) {
                        $toInsert.insertAfter(prev);
                    } else if (next) {
                        $toInsert.insertBefore(next);
                    } else {
                        $toInsertParent.prepend($toInsert);
                    }

                    var $target = $toInsert;
                    this._updateDroppedSnippet($target);

                    this.options.wysiwyg.odooEditor.observerUnactive('dragAndDropCreateSnippet');
                    await this._scrollToSnippet($target, this.$scrollable);
                    this.options.wysiwyg.odooEditor.observerActive('dragAndDropCreateSnippet');

                    browser.setTimeout(async () => {
                        // Free the mutex now to allow following operations
                        // (mutexed as well).
                        dragAndDropResolve();

                        this.__postSnippetDropExtraActions = () => {
                            // Restore editor to its normal edition state, also
                            // make sure the undroppable snippets are updated.
                            this._disableUndroppableSnippets();
                            this.options.wysiwyg.odooEditor.unbreakableStepUnactive();
                            this.options.wysiwyg.odooEditor.historyStep();
                            this.$el.find('.oe_snippet_thumbnail').removeClass('o_we_already_dragging');
                        };
                        await this.callPostSnippetDrop($target);
                    });
                } else {
                    $toInsert.remove();
                    if (dragAndDropResolve) {
                        dragAndDropResolve();
                    }
                    this.$el.find('.oe_snippet_thumbnail').removeClass('o_we_already_dragging');
                }
                this.trigger_up('drop_zone_stop');
            },
        });
        this.draggableComponent = useDragAndDrop({ ref: { el: this.el }, ...dragAndDropOptions });
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
            // By default, we don't want the `o_default_snippet_text` class on
            // custom snippets. Those are most likely already ready, we don't
            // really need the auto-selection by the editor.
            $in = this.$snippets.find('.oe_snippet_body:not(.s_custom_snippet)');
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
        this._hideTooltips();
        this._closeWidgets();

        // In translation mode, only the options tab is available.
        if (this.options.enableTranslation) {
            tab = this.tabs.OPTIONS;
        }

        this._currentTab = tab || this.tabs.BLOCKS;

        if (this._$toolbarContainer) {
            this._$toolbarContainer[0].remove();
        }
        this._$toolbarContainer = null;
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
        if (modalEl && !$(modalEl).hasScrollableContent()) {
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
    /**
     * Hides the active tooltips.
     *
     * The BS documentation says that "Tooltips that use delegation (which are
     * created using the selector option) cannot be individually destroyed on
     * descendant trigger elements". So this function should be useful to remove
     * the active tooltips manually.
     * For instance, without this, clicking on "Hide in Desktop" on a snippet
     * will leave the tooltip "forever" visible even if the "Hide in Desktop"
     * button is gone.
     *
     * @private
     */
    _hideTooltips() {
        // While functionally there is probably no way to have multiple active
        // tooltips, it is possible that the panel contains multiple tooltip
        // descriptions (we do not know what is in customers' own saved snippets
        // for example). In any case, it does not hurt to technically consider
        // the case anyway.
        const tooltipTargetEls = this.el.querySelectorAll('[aria-describedby^="tooltip"]');
        for (const el of tooltipTargetEls) {
            Tooltip.getInstance(el)?.hide();
        }
    },
    /**
     * Returns whether the edited content is a mobile view content.
     *
     * @returns {boolean}
     */
    _isMobile() {
        return weUtils.isMobileView(this.$body[0]);
    },
    /**
     * @private
     */
    _allowParentsEditors($snippet) {
        return !this.options.enableTranslation
            && !$snippet[0].classList.contains("o_no_parent_editor");
    },
    /**
     * @private
     */
    _allowInTranslationMode($snippet) {
        return globalSelector.is($snippet, { onlyTextOptions: true });
    },
    /**
     * Allows to update the snippets to build & adapt dynamic content right
     * after adding it to the DOM.
     *
     * @private
     */
    _updateDroppedSnippet($target) {
        if ($target[0].classList.contains("o_snippet_drop_in_only")) {
            // If it's a "drop in only" snippet, after dropping
            // it, we modify it so that it's no longer a
            // draggable snippet but rather simple HTML code, as
            // if the element had been created with the editor.
            $target[0].classList.remove("o_snippet_drop_in_only");
            delete $target[0].dataset.snippet;
            delete $target[0].dataset.name;
        }
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
        // Clicking in the page should be ignored on save
        if (this.options.wysiwyg.isSaving()) {
            return;
        }

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
        browser.setTimeout(() => {
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
        this._activateInsertionZones(ev.data.$selectorSiblings, ev.data.$selectorChildren, ev.data.canBeSanitizedUnless, ev.data.toInsertInline, ev.data.selectorGrids, ev.data.fromIframe);
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
     * Called when a child editor asks to clean the UI of a snippet.
     *
     * @private
     * @param {OdooEvent} ev
     */
    _onCleanUIRequest(ev) {
        const targetEditors = this.snippetEditors.filter(editor => {
            return ev.data.targetEl.contains(editor.$target[0]);
        });
        Promise.all(targetEditors.map(editor => editor.cleanUI())).then(() => {
            ev.data.onSuccess();
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
        const visibleConditionalEls = [];
        for (const snippetEditor of this.snippetEditors) {
            const targetEl = snippetEditor.$target[0];
            if (targetEl.dataset["visibility"] === "conditional" &&
                !targetEl.classList.contains("o_conditional_hidden")) {
                visibleConditionalEls.push(targetEl);
            }
        }
        const modalEl = ev.data.$snippet[0].closest('.modal');
        const carouselItemEl = ev.data.$snippet[0].closest('.carousel-item');
        // If the snippet is in a modal, destroy editors only in that modal.
        // This to prevent the modal from closing because of the cleanForSave
        // on each editors. Same thing for 'carousel-item', otherwise all the
        // editors of the 'carousel' are destroyed and the 'carousel' jumps to
        // first slide.
        await this._destroyEditors(carouselItemEl ? $(carouselItemEl) : modalEl ? $(modalEl) : null);
        await this._activateSnippet(ev.data.$snippet);
        // Because of _destroyEditors(), all the snippets with a conditional
        // visibility are hidden. Show the ones that were visible before the
        // drag and drop.
        for (const visibleConditionalEl of visibleConditionalEls) {
            visibleConditionalEl.classList.remove("o_conditional_hidden");
            delete visibleConditionalEl.dataset["invisible"];
        }
        // Update the "Invisible Elements" panel as the order of invisible
        // snippets could have changed on the page.
        await this._updateInvisibleDOM();
    },
    /**
     * Transforms an event coming from a touch screen into a mouse event.
     *
     * @private
     * @param {Event} ev - a touch event
     */
    _onTouchEvent(ev) {
        if (ev.touches.length > 1) {
            // Ignore multi-touch events.
            return;
        }
        const touch = ev.changedTouches[0];
        const touchToMouse = {
            touchstart: "mousedown",
            touchmove: "mousemove",
            touchend: "mouseup"
        };
        const simulatedEvent = new MouseEvent(touchToMouse[ev.type], {
            screenX: touch.screenX,
            screenY: touch.screenY,
            clientX: touch.clientX,
            clientY: touch.clientY,
            button: 0, // left mouse button
            bubbles: true,
            cancelable: true,
        });
        touch.target.dispatchEvent(simulatedEvent);
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
        var $snippet = $(ev.currentTarget).closest('[data-module-id]');
        var moduleID = $snippet.data('moduleId');
        var name = $snippet.attr('name');
        const bodyText = _t("Do you want to install %s App?", name);
        const linkText = _t("More info about this app.");
        const linkUrl = '/web#id=' + encodeURIComponent(moduleID) + '&view_type=form&model=ir.module.module&action=base.open_module_tree';
        this.dialog.add(ConfirmationDialog, {
            title: _t("Install %s", name),
            body: markup(`${escape(bodyText)}\n<a href="${linkUrl}" target="_blank">${escape(linkText)}</a>`),
            confirm: async () => {
                try {
                    await this.orm.call("ir.module.module", "button_immediate_install", [[moduleID]]);
                    this.trigger_up('request_save', {
                        invalidateSnippetCache: true,
                        _toMutex: true,
                        reloadWebClient: true,
                    });
                } catch (e) {
                    if (e instanceof RPCError) {
                        const message = escape(_t("Could not install module %s", name));
                        this.notification.add(message, {
                            type: "danger",
                            sticky: true,
                        });
                    } else {
                        throw e;
                    }
                }
            },
            confirmLabel: _t("Save and Install"),
            cancel: () => {},
        });
    },
    /**
     * @private
     * @param {Event} ev
     */
    _onInvisibleEntryClick: async function (ev) {
        ev.preventDefault();
        const $snippet = $(this.invisibleDOMMap.get(ev.currentTarget));
        $snippet.__force_create_editor = true;
        const isVisible = await this._execWithLoadingEffect(async () => {
            const editor = await this._createSnippetEditor($snippet);
            const show = editor.toggleTargetVisibility();
            this._disableUndroppableSnippets();
            return show;
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
        const message = _t("Are you sure you want to delete the snippet %s?", $snippet[0].getAttribute("name"));
        this.dialog.add(ConfirmationDialog, {
            body: message,
            confirm: async () => {
                await this.orm.call("ir.ui.view", "delete_snippet", [], {
                    'view_id': snippetId,
                    'template_key': this.options.snippets,
                });
                await this._loadSnippetsTemplates(true);
            },
            cancel: () => null,
            confirmLabel: _t("Yes"),
            cancelLabel: _t("No"),
        });
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
                    <we-button class="o_we_confirm_btn o_we_text_success fa fa-check" title="${confirmText}"></we-button>
                    <we-button class="o_we_cancel_btn o_we_text_danger fa fa-times" title="${cancelText}"></we-button>
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
                    await this.orm.call("ir.ui.view", "rename_snippet", [], {
                        'name': name,
                        'view_id': parseInt(ev.target.dataset.snippetId),
                        'template_key': this.options.snippets,
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
    },
    /**
     * @private
     */
    _onMouseUp(ev) {
        const snippetEl = ev.target.closest('.oe_snippet');
        if (snippetEl && !snippetEl.querySelector(".o_we_already_dragging")
                    && !ev.target.matches(".o_rename_btn")) {
            this._showSnippetTooltip($(snippetEl));
        }
    },
    /**
     * Displays an autofading tooltip over a snippet, after a delay.
     * If in the meantime the user has started to drag the snippet, it won't be
     * shown.
     *
     * TODO: remove delay param in master
     *
     * @private
     * @param {jQuery} $snippet
     * @param {Number} [delay=1500]
     */
    _showSnippetTooltip($snippet, delay = 1500) {
        this.$snippets.not($snippet).tooltip('hide');
        $snippet.tooltip('show');
        this._hideSnippetTooltips(1500);
    },
    /**
     * @private
     * @param {Number} [delay=0]
     */
    _hideSnippetTooltips(delay = 0) {
        clearTimeout(this.__hideSnippetTooltipTimeout);
        this.__hideSnippetTooltipTimeout = setTimeout(() => {
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
        this._buttonClick(async (after) => {
            await this.postSnippetDropPromise;
            return this._execWithLoadingEffect(async () => {
                const oldOnFailure = data.onFailure;
                data.onFailure = () => {
                    if (oldOnFailure) {
                        oldOnFailure();
                    }
                    after();
                };
                this.trigger_up('request_save', data);
            }, true);
        }, this.$el[0].querySelector('button[data-action=save]'));
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
        if (this.options.wysiwyg.isSaving()) {
            // Do not update the option visibilities if we are destroying them.
            return;
        }
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
    /**
     * Called when a child editor asks to update the "Invisible Elements" panel.
     *
     * @private
     */
    async _onUpdateInvisibleDom() {
        await this._updateInvisibleDOM();
    },
    _addToolbar(toolbarMode = "text") {
        if (this.folded) {
            return;
        }
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
        // Create toolbar custom container.
        this._$toolbarContainer = $('<WE-CUSTOMIZEBLOCK-OPTIONS id="o_we_editor_toolbar_container"/>');
        const $title = $("<we-title><span>" + titleText + "</span></we-title>");
        this._$toolbarContainer.append($title);
        // In case, the snippetEditor is inside an iframe, rebind the dropdown
        // from the iframe.
        for (const dropdown of this._toolbarWrapperEl.querySelectorAll('.colorpicker-group')) {
            const $ = dropdown.ownerDocument.defaultView.$;
            const $dropdown = $(dropdown);
            $dropdown.off('show.bs.dropdown');
            $dropdown.on('show.bs.dropdown', () => {
                this.options.wysiwyg.onColorpaletteDropdownShow(dropdown.dataset.colorType);
            });
            $dropdown.off('hide.bs.dropdown');
            $dropdown.on('hide.bs.dropdown', (ev) => this.options.wysiwyg.onColorpaletteDropdownHide(ev));
        }
        this._$toolbarContainer.append(this._toolbarWrapperEl);
        $(this.customizePanel).append(this._$toolbarContainer);

        // Create table-options custom container.
        const customizeTableBlock = renderToElement('web_editor.toolbar.table-options');
        this.options.wysiwyg.odooEditor.bindExecCommand(customizeTableBlock);
        $(this.customizePanel).append(customizeTableBlock);
        this._removeFormatButton = this._removeFormatButton || this._toolbarWrapperEl.querySelector('#removeFormat');
        $title.append(this._removeFormatButton);
        this._$toolbarContainer.append(this._toolbarWrapperEl);

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
            !$currentSelectionTarget.parents('#wrapwrap, .iframe-editor-wrapper').length ||
            closestElement(selection.anchorNode, '[data-oe-model]:not([data-oe-type="html"]):not([data-oe-field="arch"]):not([data-oe-translation-initial-sha])') ||
            closestElement(selection.focusNode, '[data-oe-model]:not([data-oe-type="html"]):not([data-oe-field="arch"]):not([data-oe-translation-initial-sha])') ||
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
        // TODO refactor things to make this more understandable -> on mobile
        // edition, update the UI. But to do it properly and inside the mutex
        // this simulates what happens when a snippet option is used.
        this._execWithLoadingEffect(async () => {
            const initialBodySize = this.$body[0].clientWidth;
            this.trigger_up('request_mobile_preview');

            // TODO needed so that mobile edition is considered before updating
            // the UI but this is clearly random. The trigger_up above should
            // properly await for the rerender somehow or, better, the UI update
            // should not depend on the mobile re-render entirely.
            let count = 0;
            do {
                await new Promise(resolve => setTimeout(resolve, 1));
            // Technically, should not be possible to fall into an infinite loop
            // but extra safety as a stable fix.
            } while (count++ < 1000 && Math.abs(this.$body[0].clientWidth - initialBodySize) < 1);

            // Reload images inside grid items so that no image disappears when
            // activating mobile preview.
            const $gridItemEls = this.getEditableArea().find('div.o_grid_item');
            for (const gridItemEl of $gridItemEls) {
                gridUtils._reloadLazyImages(gridItemEl);
            }

            const isMobilePreview = weUtils.isMobileView(this.$body[0]);
            for (const invisibleOverrideEl of this.getEditableArea().find('.o_snippet_mobile_invisible, .o_snippet_desktop_invisible')) {
                const isMobileHidden = invisibleOverrideEl.classList.contains("o_snippet_mobile_invisible");
                invisibleOverrideEl.classList.remove('o_snippet_override_invisible');
                if (isMobilePreview === isMobileHidden) {
                    invisibleOverrideEl.dataset.invisible = '1';
                } else {
                    delete invisibleOverrideEl.dataset.invisible;
                }
            }

            // This is async but using the main editor mutex, currently locked.
            this._updateInvisibleDOM();

            return new Promise(resolve => {
                this.trigger_up('snippet_option_update', {
                    onSuccess: () => resolve(),
                });
            });
        }, false);
    },
    /**
     * Undo..
     */
    _onUndo: async function () {
        this.options.wysiwyg.undo();
    },
    /**
     * Redo.
     */
    _onRedo: async function () {
        this.options.wysiwyg.redo();
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
        // Remove the tooltips now, because the button will be disabled and so,
        // the tooltip will not be removable (see BS doc).
        this._hideTooltips();
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

export default {
    SnippetsMenu: SnippetsMenu,
    SnippetEditor: SnippetEditor,
    globalSelector: globalSelector,
};
