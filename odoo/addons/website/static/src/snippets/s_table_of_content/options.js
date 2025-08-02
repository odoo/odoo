/** @odoo-module **/

import options from "@web_editor/js/editor/snippets.options";

options.registry.TableOfContent = options.Class.extend({
    /**
     * @override
     */
    start: function () {
        this.targetedElements = 'h1, h2';
        this.oldHeadingsEls = [];
        this.oldHeadingsDesktopVisible = [];
        const $headings = this.$target.find(this.targetedElements);
        if ($headings.length > 0) {
            this._generateNav();
        }
        // Generate the navbar if the content changes
        const targetNode = this.$target.find('.s_table_of_content_main')[0];
        const config = {attributes: false, childList: true, subtree: true, characterData: true};
        this.observer = new MutationObserver(() => this._generateNav());
        this.observer.observe(targetNode, config);
        // The mutation observer doesn't observe the attributes change, it would
        // be too much. Adding content_changed "listener" instead.
        this.$target.on('content_changed', () => this._generateNav());
        return this._super(...arguments);
    },
    /**
     * @override
     */
    destroy: function () {
        // The observer needs to be disconnected first.
        this.observer.disconnect();
        this._super(...arguments);
    },
    /**
     * @override
     */
    onRemove() {
        this._disposeScrollSpy();
        const exception = (tocEl) => tocEl === this.$target[0];
        this._activateScrollSpy(exception);
    },
    /**
     * @override
     */
    onClone: function () {
        this._generateNav();
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @param  {Function} exception
     */
    _activateScrollSpy(exception) {
        for (const tocEl of this.ownerDocument.querySelectorAll('#wrapwrap .s_table_of_content')) {
            if (exception(tocEl)) {
                continue;
            }
            this.trigger_up('widgets_start_request', {
                $target: $(tocEl),
                editableMode: true,
            });
        }
    },
    /**
     * @private
     */
    _disposeScrollSpy() {
        const scrollingEl = $().getScrollingElement(this.ownerDocument)[0];
        const scrollSpyInstance =
            this.$target[0].ownerDocument.defaultView.ScrollSpy.getInstance(scrollingEl);
        if (scrollSpyInstance) {
            scrollSpyInstance.dispose();
        }
    },
    /**
     * Returns the TOC id and the heading id from a header element.
     *
     * @param {HTMLElement} headingEl - A header element of the TOC.
     * @returns {Object}
     */
    _getTocAndHeadingId(headingEl) {
        const match = /^table_of_content_heading_(\d+)_(\d+)$/.exec(headingEl.getAttribute("id"));
        if (match) {
            return { tocId: parseInt(match[1]), headingId: parseInt(match[2]) };
        }
        return { tocId: 0, headingId: 0 };
    },
    /**
     * @private
     */
    _generateNav: function (ev) {
        const blockTextContent = this.$target[0].textContent.replaceAll('\n', '').trim();
        if (blockTextContent === '') {
            // destroy public widget and remove the ToC since there are no more
            // child elements, before doing so the observer needs to be
            // disconnected else observer observe mutation and _generateNav
            // gets called even after there's no more ToC.
            this.observer.disconnect();
            this.trigger_up('remove_snippet', {$snippet: this.$target});
            return;
        }
        this.options.wysiwyg && this.options.wysiwyg.odooEditor.unbreakableStepUnactive();
        const navEl = this.$target[0].querySelector('.s_table_of_content_navbar');
        const headingsEls = this.$target.find(this.targetedElements).toArray();
        const areHeadingsEqual = this.oldHeadingsEls.length === headingsEls.length
            && this.oldHeadingsEls.every((el, i) =>
                el.isEqualNode(headingsEls[i])
                && this.oldHeadingsDesktopVisible[i] === !headingsEls[i].closest(".o_snippet_desktop_invisible")
            );
        const areVisibilityIdsEqual = headingsEls.every((headingEl) => {
            const visibilityId = headingEl.closest('section').getAttribute('data-visibility-id');
            const matchingLinkEl = navEl.querySelector(`a[href="#${headingEl.getAttribute('id')}"]`);
            const matchingLinkVisibilityId = matchingLinkEl ? matchingLinkEl.getAttribute('data-visibility-id') : null;
            // Check if visibilityId matches matchingLinkVisibilityId or both
            // are null/undefined
            return visibilityId === matchingLinkVisibilityId;
        });
        if (areHeadingsEqual && areVisibilityIdsEqual) {
            // If the content of the navbar before the change of the DOM is
            // equal to the content of the navbar after the change of the DOM,
            // then there is no need to regenerate the navbar.
            // This is especially important as to regenerate it, we also have
            // to restart scrollSpy, which is done by restarting widgets. But
            // restarting all widgets inside the ToC would certainly lead to
            // DOM changes... which would then regenerate the navbar and lead to
            // an infinite loop.
            return;
        }
        // We dispose the scrollSpy because the navbar will be updated.
        this._disposeScrollSpy();

        const firstHeadingEl = headingsEls[0];
        let tocId = firstHeadingEl ? this._getTocAndHeadingId(firstHeadingEl).tocId : 0;
        const tocEls = this.$target[0].ownerDocument.body.querySelectorAll("[data-snippet='s_table_of_content']");
        const otherTocEls = [...tocEls].filter(tocEl => tocEl !== this.$target[0]);
        const otherTocIds = otherTocEls.map(tocEl => {
            const firstHeadingEl = tocEl.querySelector(this.targetedElements);
            return this._getTocAndHeadingId(firstHeadingEl).tocId;
        });
        if (!tocId || otherTocIds.includes(tocId)) {
            tocId = 1 + Math.max(0, ...otherTocIds);
        }
        const headingIds = headingsEls.map(headingEl => this._getTocAndHeadingId(headingEl).headingId);
        let maxHeadingIds = Math.max(0, ...headingIds);

        navEl.innerHTML = '';
        const uniqueHeadingIds = new Set();
        headingsEls.forEach((el) => {
            const $el = $(el);
            let headingId = this._getTocAndHeadingId(el).headingId;
            if (headingId) {
                // Reset headingId on duplicate.
                if (uniqueHeadingIds.has(headingId)) {
                    headingId = 0;
                } else {
                    uniqueHeadingIds.add(headingId);
                }
            }
            if (!headingId) {
                maxHeadingIds += 1;
                headingId = maxHeadingIds;
            }
            // Generate stable ids so that external links to heading anchors do
            // not get broken next time the navigation links are re-generated.
            const id = `table_of_content_heading_${tocId}_${headingId}`;
            $el.attr('id', id);
            if (!el.closest('.o_snippet_desktop_invisible')) {
                // Generate navigation entry only for desktop.
                const visibilityId = $el.closest('section').attr('data-visibility-id');
                $('<a>').attr({ 'href': "#" + id, 'data-visibility-id': visibilityId })
                        .addClass('table_of_content_link list-group-item list-group-item-action py-2 border-0 rounded-0')
                        .text($el.text())
                        .appendTo(navEl);
                $el[0].dataset.anchor = 'true';
            }
        });
        const exception = (tocEl) => !tocEl.querySelector('.s_table_of_content_navbar a');
        this._activateScrollSpy(exception);
        this.oldHeadingsEls = [...headingsEls.map(el => el.cloneNode(true))];
        this.oldHeadingsDesktopVisible = [...headingsEls.map(el => !el.closest('.o_snippet_desktop_invisible'))];
    },
});

options.registry.TableOfContentNavbar = options.Class.extend({

    //--------------------------------------------------------------------------
    // Options
    //--------------------------------------------------------------------------

    /**
     * Change the navbar position.
     *
     * @see this.selectClass for parameters
     */
    navbarPosition: function (previewMode, widgetValue, params) {
        const $navbar = this.$target;
        const $mainContent = this.$target.parent().find('.s_table_of_content_main');
        if (widgetValue === 'top' || widgetValue === 'left') {
            $navbar.prev().before($navbar);
        }
        if (widgetValue === 'left' || widgetValue === 'right') {
            $navbar.removeClass('s_table_of_content_horizontal_navbar col-lg-12').addClass('s_table_of_content_vertical_navbar col-lg-3');
            $mainContent.removeClass('col-lg-12').addClass('col-lg-9');
            $navbar.find('.s_table_of_content_navbar').removeClass('list-group-horizontal-md');
        }
        if (widgetValue === 'right') {
            $navbar.next().after($navbar);
        }
        if (widgetValue === 'top') {
            $navbar.removeClass('s_table_of_content_vertical_navbar col-lg-3').addClass('s_table_of_content_horizontal_navbar col-lg-12');
            $navbar.find('.s_table_of_content_navbar').addClass('list-group-horizontal-md');
            $mainContent.removeClass('col-lg-9').addClass('col-lg-12');
        }
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _computeWidgetState: function (methodName, params) {
        switch (methodName) {
            case 'navbarPosition': {
                const $navbar = this.$target;
                if ($navbar.hasClass('s_table_of_content_horizontal_navbar')) {
                    return 'top';
                } else {
                    const $mainContent = $navbar.parent().find('.s_table_of_content_main');
                    return $navbar.prev().is($mainContent) === true ? 'right' : 'left';
                }
            }
        }
        return this._super(...arguments);
    },
});

options.registry.TableOfContentMainColumns = options.Class.extend({
    forceNoDeleteButton: true,
});
