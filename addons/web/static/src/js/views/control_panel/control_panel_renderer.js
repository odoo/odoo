odoo.define('web.ControlPanelRenderer', function (require) {
"use strict";

var AbstractRenderer = require('web.AbstractRenderer');
var data = require('web.data');
var viewUtils = require('web.viewUtils');

var ControlPanelRenderer = AbstractRenderer.extend({
    template: 'ControlPanel',
    events: _.extend({}, AbstractRenderer.prototype.events, {
        'click.bs.dropdown .o_search_options .dropdown-menu': '_onDropdownClicked',
    }),

    /**
     * @override
     * @param {Object[]} [params.controls=[]] list of nodes to render in the
     *   buttons area.
     * @param {String} [params.template] the QWeb template to render the
     *   ControlPanel. By default, the template 'ControlPanel' will be used.
     */
    init: function (parent, state, params) {
        this._super.apply(this, arguments);
        this.controls = params.controls || [];
        if (params.template) {
            this.template = params.template;
        }
    },
    /**
     * Renders the control panel and creates a dictionnary of its exposed
     * elements
     *
     * @override
     */
    start: function () {
        var self = this;

        // exposed jQuery nodesets
        this.nodes = {
            $buttons: this.$('.o_cp_buttons'),
            $pager: this.$('.o_cp_pager'),
            $searchview: this.$('.o_cp_searchview'),
            $searchview_buttons: this.$('.o_search_options'),
            $sidebar: this.$('.o_cp_sidebar'),
            $switch_buttons: this.$('.o_cp_switch_buttons'),
        };

        this.$controls = $('<div>', {class: 'o_cp_custom_buttons'});
        var hasCustomButtons = false;
        this.controls.forEach(function (node) {
            if (node.tag === 'button') {
                hasCustomButtons = true;
                self.$controls.append(self._renderButton(node));
            }
        });
        if (!hasCustomButtons) {
            this.$controls = $(); // fixme: this is to prevent the controlpanel
                                  // bottom row to take 5px height due to padding
        }

        this.render({});

        return this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @param {Object} [status.active_view] the current active view
     * @param {Array} [status.breadcrumbs] the breadcrumbs to display (see _render_breadcrumbs() for
     * precise description)
     * @param {Object} [status.cp_content] dictionnary containing the new ControlPanel jQuery elements
     * @param {Boolean} [status.hidden] true if the ControlPanel should be hidden
     * @param {openerp.web.SearchView} [status.searchview] the searchview widget
     * @param {Boolean} [status.search_view_hidden] true if the searchview is hidden, false otherwise
     * @param {Boolean} [options.clear] set to true to clear from control panel
     * elements that are not in status.cp_content
     */
    render: function (status, options) {
        this._toggleVisibility(!status.hidden);

        // Don't update the ControlPanel in headless mode as the views have
        // inserted themselves the buttons where they want, so inserting them
        // again in the ControlPanel will remove them from where they should be
        if (!status.hidden) {
            options = _.defaults({}, options, {
                clear: true, // clear control panel by default
            });
            var new_cp_content = status.cp_content || {};

            // Detach special controls
            this.$controls.detach();

            // Render the breadcrumbs
            if (status.breadcrumbs) {
                this.$('.breadcrumb').html(this._renderBreadcrumbs(status.breadcrumbs));
            }

            // Detach control_panel old content and attach new elements
            var toDetach = this.nodes;
            if (status.searchview && this.searchview === status.searchview) {
                // If the searchview is the same as before, don't detach it s.t.
                // we don't loose any floating content, nor the focus
                toDetach = _.omit(toDetach, '$searchview');
                new_cp_content = _.omit(new_cp_content, '$searchview');
            }
            if (options.clear) {
                this._detachContent(toDetach);
                // Show the searchview buttons area, which might have been hidden by
                // the searchview, as client actions may insert elements into it
                this.nodes.$searchview_buttons.show();
            } else {
                this._detachContent(_.pick(toDetach, _.keys(new_cp_content)));
            }
            this._attachContent(new_cp_content);
            if (options.clear || status.searchview) {
                this.searchview = status.searchview;
            }

            // Update the searchview and switch buttons
            if (status.searchview || options.clear) {
                this._updateSearchView(status.searchview, status.search_view_hidden, status.groupable, status.enableTimeRangeMenu);
            }
            if (status.active_view_selector) {
                this._updateSwitchButtons(status.active_view_selector);
            }

            // Attach special controls
            this.$controls.prependTo(this.nodes.$buttons);
        }
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {Object} content dictionnary of jQuery elements to attach, whose
     *   keys are jQuery nodes identifiers in this.nodes
     */
    _attachContent: function (content) {
        for (var $element in content) {
            var $nodeset = content[$element];
            if ($nodeset && this.nodes[$element]) {
                this.nodes[$element].append($nodeset);
            }
        }
    },
    /**
     * @private
     * @param {Object} content subset of this.nodes to detach
     */
    _detachContent: function (content) {
        for (var $element in content) {
            content[$element].contents().detach();
        }
    },
    /**
     * @private
     * @param {Array} breadcrumbs list of objects containing the following keys:
     *   - action: the action to execute when clicking on this part of the
     *       breadcrumbs
     *   - index: the index in the breadcrumbs (starting at 0)
     *   - title: what to display in the breadcrumbs
     * @return {Array} list of breadcrumbs' li jQuery elements
     */
    _renderBreadcrumbs: function (breadcrumbs) {
        var self = this;
        return breadcrumbs.map(function (bc, index) {
            return self._renderBreadcrumbsItem(bc, index, breadcrumbs.length);
        });
    },
    /**
     * Renders a button to display in the buttons area, given an arch's node.
     *
     * @private
     * @param {Object} node
     */
    _renderButton: function (node) {
        var self = this;
        var $button = viewUtils.renderButtonFromNode(node);
        $button.on('click', function () {
            self.trigger_up('button_clicked', {
                attrs: node.attrs,
            });
        });
        return $button;
    },
    /**
     * Renders a breadcrumbs' li Jquery element
     *
     * @private
     */
    _renderBreadcrumbsItem: function (bc, index, length) {
        var self = this;
        var is_last = (index === length-1);
        var li_content = bc.title && _.escape(bc.title.trim()) || data.noDisplayContent;
        var $bc = $('<li>', {class: 'breadcrumb-item'})
            .append(is_last ? li_content : $('<a>', {href: '#'}).html(li_content))
            .toggleClass('active', is_last);
        if (!is_last) {
            $bc.click(function (ev) {
                ev.preventDefault();
                self.trigger_up('breadcrumb_clicked', {controllerID: bc.controllerID});
            });
        }
        return $bc;
    },
    /**
     * Toggles the visibility of the ControlPanel and detaches or attaches its
     * contents to clean the DOM
     *
     * @private
     * @param {boolean} visible true to show the control panel, false to hide it
     */
    _toggleVisibility: function (visible) {
        this.do_toggle(visible);
        if (!visible && !this.$content) {
            this.$content = this.$el.contents().detach();
        } else if (this.$content) {
            this.$content.appendTo(this.$el);
            this.$content = null;
        }
    },
    /**
     * Updates the SearchView's visibility and extends the breadcrumbs area if
     * the SearchView is not visible
     *
     * @private
     * @param {SearchView} searchview a SearchView instance
     * @param {boolean} isHidden visibility of the searchview
     * @param {boolean} groupable visibility of the groupable menu (only
     *   relevant if searchview is visible)
     * @param {boolean} enableTimeRangeMenu visibility of the time range menu
     *   (only relevant if searchview is visible)
     */
    _updateSearchView: function (searchview, isHidden, groupable, enableTimeRangeMenu) {
        if (searchview) {
            searchview.toggle_visibility(!isHidden);
            if (groupable !== undefined){
                searchview.groupby_menu.do_toggle(groupable);
            }
            if (enableTimeRangeMenu !== undefined){
                searchview.displayTimeRangeMenu(enableTimeRangeMenu);
            }
        }
        this.nodes.$searchview.toggle(!isHidden);
        this.$el.toggleClass('o_breadcrumb_full', !!isHidden);
    },
    /**
     * Removes active class on all switch-buttons and adds it to the one of the
     * active view
     *
     * @private
     * @param {string} selector the selector of the div to activate
     */
    _updateSwitchButtons: function (selector) {
        this.nodes.$switch_buttons.find('button').removeClass('active');
        this.$(selector).addClass('active');
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onButtonClicked: function (ev) {
        this.trigger_up('button_clicked', {});
    },
    /**
     * Prevents the search dropdowns from closing when clicking inside them.
     *
     * @private
     * @param {MouseEvent} ev
     */
    _onDropdownClicked: function (ev) {
        ev.stopPropagation();
    },
});

return ControlPanelRenderer;

});
