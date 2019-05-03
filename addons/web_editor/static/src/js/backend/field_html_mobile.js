odoo.define('web_editor.field.html.mobile', function (require) {
'use strict';

var config = require('web.config');
if (!config.device.isMobile) {
    return;
}

var FieldHtml = require('web_editor.field.html');
FieldHtml.include({
    /**
     * Append throttle function for event append inside the _onLoadWysiwyg
     * @override
     */
    init: function () {
        this._super.apply(this, arguments);
        // Create a reference for bind function
        this._throttleComputeScrollBarIconPosition = _.throttle(this._computeScrollBarIconPosition.bind(this), 100);
        this._throttleHideDropdownMenuShow = _.throttle(this._hideDropdownMenuShow.bind(this), 100);
    },
    /**
     * Unregister all event bind on the _onLoadWysiwyg
     *
     * @override
     */
    destroy: function () {
        var toolbarNode = this._queryContentNode('.note-toolbar');
        if (toolbarNode != null) {
            toolbarNode.removeEventListener('scroll', this._throttleComputeScrollBarIconPosition);
        }
        document.removeEventListener('scroll', this._throttleHideDropdownMenuShow);
        this._super.apply(this, arguments);
    },
    // --------------------------------------------------------------------------
    // Public
    // --------------------------------------------------------------------------
    /**
     * Append event scroll on note-toolbar node if it's needed (has scrollbar)
     *
     * @private
     */
    _appendScrollIcon: function () {
        var toolbarNode = this._queryContentNode('.note-toolbar');
        if (toolbarNode == null) {
            return;
        }
        var hasScrollBarWidth = toolbarNode.scrollWidth > toolbarNode.offsetWidth;
        var toolbarWrapperNode = this._queryContentNode('.note-toolbar-wrapper');
        if (hasScrollBarWidth && toolbarWrapperNode) {
            toolbarWrapperNode.classList.add('note-toolbar-scrollable');
            toolbarNode.addEventListener('scroll', this._throttleComputeScrollBarIconPosition.bind(this));
            this._throttleComputeScrollBarIconPosition();
        }
    },
    /**
     * Determine if the note-toolbar node needed to show the scrollable-start and scrollable-end
     *
     * @private
     * @param {Event} ev
     */
    _computeScrollBarIconPosition: function (ev) {
        if (ev) {
            ev.preventDefault();
        }
        var toolbarNode = this._queryContentNode('.note-toolbar');
        if (toolbarNode == null) {
            return;
        }

        var hasScrollbarAtBegin = toolbarNode.scrollLeft == 0;
        this._computeToolBarWrapperScrollableClass('scrollable-start', hasScrollbarAtBegin);
        var hasScrollbarAtEnd = toolbarNode.scrollWidth == toolbarNode.clientWidth + toolbarNode.scrollLeft;
        this._computeToolBarWrapperScrollableClass('scrollable-end', hasScrollbarAtEnd);
    },
    /**
     * Determine if we can apply a given class on note-toolbar-wrapper node
     *
     * @private
     * @param {String} className
     * @param {boolean} canRemoveClass
     */
    _computeToolBarWrapperScrollableClass: function (className, canRemoveClass) {
        var toolbarWrapperNode = this._queryContentNode('.note-toolbar-wrapper');
        if (toolbarWrapperNode == null) {
            return;
        }

        if (canRemoveClass) {
            toolbarWrapperNode.classList.remove(className);
        } else if (!toolbarWrapperNode.classList.contains(className)) {
            toolbarWrapperNode.classList.add(className);
        }
    },
    /**
     * Hide the dropdown menu show in the toolbar
     *
     * @private
     */
    _hideDropdownMenuShow: function () {
        var dropdown = this._queryContentNode('.note-toolbar .note-btn-group.show > .dropdown-menu.show');
        if (dropdown != null) {
            var dropdownToggleBtn = dropdown.parentNode.querySelector('.dropdown-toggle');
            if (dropdownToggleBtn != null) {
                dropdownToggleBtn.click();
            }
        }
    },
    /**
     * Append :
     *   - additional event (toolbar scroll, hide open dropdown when user scroll
     *   - Append cancel attribute on dropdown (useful for css)
     *
     * @override
     */
    _onLoadWysiwyg: function () {
        this._super.apply(this, arguments);

        document.addEventListener('scroll', this._throttleHideDropdownMenuShow.bind(this));
        // use a setTimeout because we need to wait the css computing and rendering for knowing
        // if an scrollbar is displayed on the screen
        setTimeout(this._appendScrollIcon.bind(this), 1);
    },
    /**
     * Helper for query the $content node using vanilla js
     *
     * @private
     * @param {String} cssSelector
     * @returns {HTMLElement}
     */
    _queryContentNode: function (cssSelector) {
        return this.$content ? this.$content.get(0).querySelector(cssSelector) : null;
    }
});

});
