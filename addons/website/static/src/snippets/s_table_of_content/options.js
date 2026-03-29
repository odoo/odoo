odoo.define('website.s_table_of_content_options', function (require) {
'use strict';

const options = require('web_editor.snippets.options');

options.registry.TableOfContent = options.Class.extend({
    /**
     * @override
     */
    start: function () {
        this.targetedElements = 'h1, h2';
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
    onClone: function () {
        this._generateNav();
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

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
        this.options.wysiwyg && this.options.wysiwyg.odooEditor.unbreakableStepUnactive();
        const firstHeadingEl = this.$target[0].querySelector(this.targetedElements);
        let tocId = firstHeadingEl ? this._getTocAndHeadingId(firstHeadingEl).tocId : 0;
        const tocEls = this.$target[0].ownerDocument.body.querySelectorAll("[data-snippet='s_table_of_content']");
        const otherTocEls = [...tocEls].filter(tocEl =>
            tocEl !== this.$target[0]
            // TODO In next version do not exclude droppable snippet.
            && !tocEl.closest("#oe_snippets")
        );
        const otherTocIds = otherTocEls.map(tocEl => {
            const firstHeadingEl = tocEl.querySelector(this.targetedElements);
            return this._getTocAndHeadingId(firstHeadingEl).tocId;
        });
        if (!tocId || otherTocIds.includes(tocId)) {
            tocId = 1 + Math.max(0, ...otherTocIds);
        }
        const $nav = this.$target.find('.s_table_of_content_navbar');
        const $headings = this.$target.find(this.targetedElements);
        const headingIds = [...$headings].map(headingEl => this._getTocAndHeadingId(headingEl).headingId);
        let maxHeadingIds = Math.max(0, ...headingIds);
        $nav.empty();
        const uniqueHeadingIds = new Set();
        _.each($headings, el => {
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
            const visibilityId = $el.closest('[data-visibility-id]').data('visibility-id');
            $('<a>').attr({ 'href': "#" + id, 'data-visibility-id': visibilityId })
                    .addClass('table_of_content_link list-group-item list-group-item-action py-2 border-0 rounded-0')
                    .text($el.text())
                    .appendTo($nav);
            $el.attr('id', id);
            $el[0].dataset.anchor = 'true';
        });
        const tocAnchorEl = this.$target[0].querySelector('a.table_of_content_link');
        if (!tocAnchorEl) {
            // destroy public widget and remove the ToC since there are no more
            // child elements.
            this.trigger_up('remove_snippet', {$snippet: this.$target});
        } else {
            $nav.find('a:first').addClass('active');
        }
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
});
