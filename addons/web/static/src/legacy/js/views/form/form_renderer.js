odoo.define('web.FormRenderer', function (require) {
"use strict";

var BasicRenderer = require('web.BasicRenderer');
var config = require('web.config');
var core = require('web.core');
var dom = require('web.dom');
var viewUtils = require('web.viewUtils');

var _t = core._t;
var qweb = core.qweb;

const scrollUtils = require("@web/core/utils/scrolling");
// symbol used as key to set the <field> node id on its widget
const symbol = Symbol('form');

var FormRenderer = BasicRenderer.extend({
    className: "o_legacy_form_view",
    events: _.extend({}, BasicRenderer.prototype.events, {
        'click .o_notification_box .oe_field_translate': '_onTranslate',
        'click .o_notification_box .btn-close': '_onTranslateNotificationClose',
        'shown.bs.tab a[data-bs-toggle="tab"]': '_onNotebookTabChanged',
        'click .o_form_label': '_onFieldLabelClicked',
    }),
    custom_events: _.extend({}, BasicRenderer.prototype.custom_events, {
        'navigation_move':'_onNavigationMove',
        'activate_next_widget' : '_onActivateNextWidget',
        'quick_edit': '_onQuickEdit',
    }),
    // default col attributes for the rendering of groups
    INNER_GROUP_COL: 2,
    OUTER_GROUP_COL: 2,
    quickEditExclusion: [
        '.o_legacy_list_view tbody',
        '.oe_button_box',
        '.oe_subtotal_footer',
    ],

    /**
     * @override
     * @param {Object} params.fieldIdsToNames maps <field> node ids to field names
     *   (useful when there are several occurrences of the same field in the arch)
     */
    init: function (parent, state, params) {
        this._super.apply(this, arguments);
        this.fieldIdsToNames = params.fieldIdsToNames;
        this.idsForLabels = {};
        this.lastActivatedFieldIndex = -1;
        this.alertFields = {};
        this.labelsToPostProcess = [];
        // The form renderer doesn't render invsible fields (invisible="1") by
        // default, to speed up the rendering. However, we sometimes have to
        // display them (e.g. in Studio, in "show invisible" mode). This flag
        // allows to disable this optimization.
        this.renderInvisible = false;
        // Keeps track of buttons that are disabled momentarily and need to be renabled.
        // Needed to compare with buttons that have to stay disabled all the time.
        this.manuallyDisabledButtons = new Set();
    },
    /**
     * @override
     */
    start: function () {
        this._applyFormSizeClass();
        return this._super.apply(this, arguments);
    },
    /**
     * Called each time the form view is attached into the DOM
     */
    on_attach_callback: function () {
        this._super.apply(this, arguments);
        core.bus.on("SCROLLER:ANCHOR_LINK_CLICKED", this, this._onAnchorLinkClicked);
    },
     /**
     * Called each time the form view is detached into the DOM
     */
    on_detach_callback: function () {
        this._super.apply(this, arguments);
        core.bus.off("SCROLLER:ANCHOR_LINK_CLICKED", this, this._onAnchorLinkClicked);
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Focuses the field having attribute 'default_focus' set, if any, or the
     * first focusable field otherwise.
     * In read mode, delegate which button to give the focus to, to the form_renderer
     *
     * @returns {int | undefined} the index of the widget activated else
     * undefined
     */
    autofocus: function () {
        if (this.mode === 'readonly') {
            var firstPrimaryFormButton =  this.$el.find('button.btn-primary:enabled:visible:first()');
            if (firstPrimaryFormButton.length > 0) {
                return firstPrimaryFormButton.focus();
            } else {
                return;
            }
        }
        var focusWidget = this.defaultFocusField;
        if (!focusWidget || !focusWidget.isFocusable()) {
            var widgets = this.allFieldWidgets[this.state.id];
            for (var i = 0; i < (widgets ? widgets.length : 0); i++) {
                var widget = widgets[i];
                if (widget.isFocusable()) {
                    focusWidget = widget;
                    break;
                }
            }
        }
        if (focusWidget) {
            return focusWidget.activate({noselect: true, noAutomaticCreate: true});
        }
    },
    /**
     * Extend the method so that labels also receive the 'o_field_invalid' class
     * if necessary.
     *
     * @override
     * @see BasicRenderer.canBeSaved
     * @param {string} recordID
     * @returns {string[]}
     */
    canBeSaved: function () {
        var fieldNames = this._super.apply(this, arguments);

        var $labels = this.$('label');
        $labels.removeClass('o_field_invalid');

        const allWidgets = this.allFieldWidgets[this.state.id] || [];
        const widgets = allWidgets.filter(w => fieldNames.includes(w.name));
        for (const widget of widgets) {
            const idForLabel = this.idsForLabels[widget[symbol]];
            if (idForLabel) {
                $labels
                    .filter('[for=' + idForLabel + ']')
                    .addClass('o_field_invalid');
            }
        }
        return fieldNames;
    },
    /*
     * Updates translation alert fields for the current state and display updated fields
     *
     *  @param {Object} alertFields
     */
    updateAlertFields: function (alertFields) {
        if (this.state.res_id) {
            this.alertFields[this.state.res_id] = _.extend(this.alertFields[this.state.res_id] || {}, alertFields);
            this.displayTranslationAlert();
        }
    },
    /**
     * Show a warning message if the user modified a translated field.  For each
     * field, the notification provides a link to edit the field's translations.
     */
    displayTranslationAlert: function () {
        this.$('.o_notification_box').remove();
        if (this.alertFields[this.state.res_id]) {
            var $notification = $(qweb.render('notification-box', {type: 'info'}))
                .append(qweb.render('translation-alert', {
                    fields: this.alertFields[this.state.res_id],
                    lang: _t.database.parameters.name
                }));
            if (this.$('.o_form_statusbar').length) {
                this.$('.o_form_statusbar').after($notification);
            } else if (this.$('.o_form_sheet_bg').length) {
                this.$('.o_form_sheet_bg').prepend($notification);
            } else {
                this.$el.prepend($notification);
            }
        }
    },
    /**
     * @see BasicRenderer.confirmChange
     *
     * We need to reapply the idForLabel postprocessing since some widgets may
     * have recomputed their dom entirely.
     *
     * @override
     */
    confirmChange: function () {
        var self = this;
        return this._super.apply(this, arguments).then(function (resetWidgets) {
            _.each(resetWidgets, function (widget) {
                self._setIDForLabel(widget, self.idsForLabels[widget[symbol]]);
            });
            if (self.$('.o_field_invalid').length) {
                self.canBeSaved(self.state.id);
            }
            self._postProcessLabels();
            return resetWidgets;
        });
    },
    /**
     * Disable statusbar buttons and stat buttons so that they can't be clicked anymore
     *
     */
    disableButtons: function () {
        const allButtons = this.$el[0].querySelectorAll('.o_statusbar_buttons button, .oe_button_box button');
        for (const button of allButtons) {
            if (!button.getAttribute("disabled")) {
                this.manuallyDisabledButtons.add(button)
                button.setAttribute("disabled", true)
            }
        }
    },
    /**
     * Enable statusbar buttons and stat buttons so they can be clicked again
     *
     */
    enableButtons: function () {
        this.manuallyDisabledButtons.forEach((button) => {
            button.removeAttribute("disabled");
        });
        this.manuallyDisabledButtons.clear();
    },
    /**
     * Put the focus on the last activated widget.
     * This function is used when closing a dialog to give the focus back to the
     * form that has opened it and ensures that the focus is in the correct
     * field.
     */
    focusLastActivatedWidget: function () {
        if (this.lastActivatedFieldIndex !== -1) {
            return this._activateNextFieldWidget(this.state, this.lastActivatedFieldIndex - 1,
                { noAutomaticCreate: true });
        }
        return false;
    },
    /**
     * returns the active tab pages for each notebook
     *
     * @todo currently, this method is unused...
     *
     * @see setLocalState
     * @returns {Object} a map from notebook name to the active tab index
     */
    getLocalState: function () {
        const state = {};
        const sheetBg = this.el.querySelector('.o_form_sheet_bg');
        if (sheetBg) {
            state.scrollValue = sheetBg.scrollTop;
        }
        for (const notebook of this.el.querySelectorAll(':scope div.o_notebook')) {
            const name = notebook.dataset.name;
            const navs = notebook.querySelectorAll(':scope .o_notebook_headers .nav-item > .nav-link');
            state[name] = Math.max([...navs].findIndex(
                nav => nav.classList.contains('active')
            ), 0);
        }
        return state;
    },
    /**
     * Quick edits the field we clicked on before the mode switch.
     *
     * @param {Object} quickEditInfo
     * @param {string} quickEditInfo.fieldName
     * @param {any} quickEditInfo.extraInfo
     */
    quickEdit: function (quickEditInfo) {
        const { fieldName, extraInfo } = quickEditInfo;
        // We cannot use the field's id because a same field could be defined
        // twice, one in edit only and the other in read only. Because of this
        // case, we have to search the field by its name and check if it is focusable.
        const fieldWidget = this.allFieldWidgets[this.state.id]
            .find(field => field.name === fieldName && field.isFocusable());
        if (fieldWidget) {
            fieldWidget.quickEdit(extraInfo);
        }
    },
    /**
     * Reset the tracking of the last activated field. The fast entry with
     * keyboard navigation needs to track the last activated field in order to
     * set the focus.
     *
     * In particular, when there are changes of mode (e.g. edit -> readonly ->
     * edit), we do not want to auto-set the focus on the previously last
     * activated field. To avoid this issue, this method should be called
     * whenever there is a change of mode.
     */
    resetLastActivatedField: function () {
        this.lastActivatedFieldIndex = -1;
    },
    /**
     * Resets state which stores information like scroll position, curently
     * active page, ...
     *
     * @override
     */
    resetLocalState() {
        for (const notebook of this.el.querySelectorAll(':scope div.o_notebook')) {
            [...notebook.querySelectorAll(':scope .o_notebook_headers .nav-item .nav-link')]
                .map(nav => nav.classList.remove('active'));
            [...notebook.querySelectorAll(':scope .tab-content > .tab-pane')]
                .map(tab => tab.classList.remove('active'));
        }

    },
    /**
     * Restore active tab pages for each notebook. It relies on the implicit fact
     * that each nav header corresponds to a tab page.
     *
     * @param {Object} state the result from a getLocalState call
     */
    setLocalState: function (state) {
        for (const notebook of this.el.querySelectorAll(':scope div.o_notebook')) {
            if (notebook.closest(".o_field_widget")) {
                continue;
            }
            const name = notebook.dataset.name;
            if (name in state) {
                const navs = notebook.querySelectorAll(':scope .o_notebook_headers .nav-item');
                const pages = notebook.querySelectorAll(':scope > .tab-content > .tab-pane');
                // We can't base the amount on the 'navs' length since some overrides
                // are adding pageless nav items.
                const validTabsAmount = pages.length;
                if (!validTabsAmount) {
                    continue; // No page defined on the notebook.
                }
                let activeIndex = state[name];
                if (navs[activeIndex].classList.contains('o_invisible_modifier')) {
                    activeIndex = [...navs].findIndex(
                        nav => !nav.classList.contains('o_invisible_modifier')
                    );
                }
                if (activeIndex <= 0) {
                    continue; // No visible tab OR first tab = active tab (no change to make).
                }
                for (let i = 0; i < validTabsAmount; i++) {
                    navs[i].querySelector('.nav-link').classList.toggle('active', activeIndex === i);
                    pages[i].classList.toggle('active', activeIndex === i);
                }
                core.bus.trigger('DOM_updated');
            }
        }
        const sheetBg = this.el.querySelector('.o_form_sheet_bg');
        if (sheetBg) {
            sheetBg.scrollTop = state.scrollValue;
        }
    },
    /**
     * @override method from AbstractRenderer
     * @param {Object} state a valid state given by the model
     * @param {Object} params
     * @param {string} [params.mode] new mode, either 'edit' or 'readonly'
     * @param {string[]} [params.fieldNames] if given, the renderer will only
     *   update the fields in this list
     * @returns {Promise}
     */
    updateState: function (state, params) {
        this._setState(state);
        this.mode = (params && 'mode' in params) ? params.mode : this.mode;

        // if fieldNames are given, we update the corresponding field widget.
        // I think this is wrong, and the caller could directly call the
        // confirmChange method
        if (params.fieldNames) {
            // only update the given fields
            return this.confirmChange(this.state, this.state.id, params.fieldNames);
        }
        return this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Activates the first visible tab from a given list of tab objects. The
     * first tab having an "autofocus" attribute set will be focused in
     * priority.
     *
     * @private
     * @param {Object[]} tabs
     */
    _activateFirstVisibleTab(tabs) {
        const visibleTabs = tabs.filter(
            (tab) => !tab.$header.hasClass("o_invisible_modifier")
        );
        const autofocusTab = visibleTabs.findIndex(
            (tab) => tab.node.attrs.autofocus === "autofocus"
        );
        const tabToFocus = visibleTabs[Math.max(0, autofocusTab)];
        if (tabToFocus) {
            tabToFocus.$header.find('.nav-link').addClass('active');
            tabToFocus.$page.addClass('active');
        }
    },
    /**
     * @override
     */
    _activateNextFieldWidget: function (record, currentIndex) {
        //if we are the last widget, we should give the focus to the first Primary Button in the form
        //else do the default behavior
        if ( (currentIndex + 1) >= (this.allFieldWidgets[record.id] || []).length) {
            this.trigger_up('focus_control_button');
            this.lastActivatedFieldIndex = -1;
        } else {
            var activatedIndex =  this._super.apply(this, arguments);
            if (activatedIndex === -1 ) { // no widget have been activated, we should go to the edit/save buttons
                this.trigger_up('focus_control_button');
                this.lastActivatedFieldIndex = -1;
            }
            else {
                this.lastActivatedFieldIndex = activatedIndex;
            }
        }
        return this.lastActivatedFieldIndex;
    },
    /**
     * Add a tooltip on a button
     *
     * @private
     * @param {Object} node
     * @param {jQuery} $button
     */
    _addButtonTooltip: function (node, $button) {
        var self = this;
        $button.tooltip({
            title: function () {
                return qweb.render('WidgetButton.tooltip', {
                    debug: config.isDebug(),
                    state: self.state,
                    node: node,
                });
            },
        });
    },
    /**
     * @private
     * @param {jQueryElement} $el
     * @param {Object} node
     */
    _addOnClickAction: function ($el, node) {
        if (node.attrs.special || node.attrs.confirm || node.attrs.type || $el.hasClass('oe_stat_button')) {
            var self = this;
            $el.on("click", function () {
                self.trigger_up('button_clicked', {
                    attrs: node.attrs,
                    record: self.state,
                });
            });
        }
    },
    _applyFormSizeClass: function () {
        const formEl = this.$el[0];
        if (config.device.size_class <= config.device.SIZES.XS) {
            formEl.classList.add('o_xxs_form_view');
        } else {
            formEl.classList.remove('o_xxs_form_view');
        }
        if (config.device.size_class === config.device.SIZES.XXL) {
            formEl.classList.add('o_xxl_form_view');
        } else {
            formEl.classList.remove('o_xxl_form_view');
        }
    },
    /**
     * @private
     * @param {string} uid a <field> node id
     * @returns {string}
     */
    _getIDForLabel: function (uid) {
        if (!this.idsForLabels[uid]) {
            this.idsForLabels[uid] = _.uniqueId('o_field_input_');
        }
        return this.idsForLabels[uid];
    },
    /**
     * @override
     * @private
     */
    _getRecord: function (recordId) {
        return this.state.id === recordId ? this.state : null;
    },
    /**
     * @override
     * @private
     */
    _postProcessField: function (widget, node) {
        this._super.apply(this, arguments);
        // set the node id on the widget, as it might be necessary later (tooltips, confirmChange...)
        widget[symbol] = node.attrs.id;
        this._setIDForLabel(widget, this._getIDForLabel(node.attrs.id));
        if (JSON.parse(node.attrs.default_focus || "0")) {
            this.defaultFocusField = widget;
        }
    },
    /**
     * This function is called once form view is rendered or modifiers are
     * changed to process labels to add o_form_label_empty.
     *
     * @private
     */
    _postProcessLabels() {
        this.labelsToPostProcess.forEach((label) => {
            label.call();
        });
        this.labelsToPostProcess = [];
    },
    /**
     * @private
     * @param {Object} node
     * @returns {jQueryElement}
     */
    _renderButtonBox: function (node) {
        var self = this;
        var $result = $('<' + node.tag + '>', {class: 'o_not_full'});

        // The rendering of buttons may be async (see renderFieldWidget), so we
        // must wait for the buttons to be ready (and their modifiers to be
        // applied) before manipulating them, as we check if they are visible or
        // not. To do so, we extract from this.defs the promises corresponding
        // to the buttonbox buttons, and wait for them to be resolved.
        var nextDefIndex = this.defs.length;
        var buttons = _.map(node.children, function (child) {
            if (child.tag === 'button') {
                return self._renderStatButton(child);
            } else {
                return self._renderNode(child);
            }
        });

        // At this point, each button is an empty div that will be replaced by
        // the real $el of the button when it is ready (with replaceWith).
        // However, this only works if the empty div is appended somewhere, so
        // we here append them into a wrapper, and unwrap them once they have
        // been replaced.
        var $tempWrapper = $('<div>');
        _.each(buttons, function ($button) {
            $button.appendTo($tempWrapper);
        });
        var defs = this.defs.slice(nextDefIndex);
        Promise.all(defs).then(function () {
            buttons = $tempWrapper.children();
            var buttons_partition = _.partition(buttons, function (button) {
                return $(button).is('.o_invisible_modifier');
            });
            var invisible_buttons = buttons_partition[0];
            var visible_buttons = buttons_partition[1];

            // Get the unfolded buttons according to window size
            var nb_buttons = self._renderButtonBoxNbButtons();
            var unfolded_buttons = visible_buttons.slice(0, nb_buttons).concat(invisible_buttons);

            // Get the folded buttons
            var folded_buttons = visible_buttons.slice(nb_buttons);
            if (folded_buttons.length === 1) {
                unfolded_buttons = buttons;
                folded_buttons = [];
            }

            // Toggle class to tell if the button box is full (CSS requirement)
            var full = (visible_buttons.length > nb_buttons);
            $result.toggleClass('o_full', full).toggleClass('o_not_full', !full);

            // Add the unfolded buttons
            _.each(unfolded_buttons, function (button) {
                $(button).appendTo($result);
            });

            // Add the dropdown with folded buttons if any
            if (folded_buttons.length) {
                $result.append(dom.renderButton({
                    attrs: {
                        'class': 'oe_stat_button o_button_more dropdown-toggle',
                        'data-bs-toggle': 'dropdown',
                    },
                    text: _t("More"),
                }));

                var $dropdown = $("<div>", {class: "dropdown-menu o_dropdown_more", role: "menu"});
                _.each(folded_buttons, function (button) {
                    $(button).addClass('dropdown-item').appendTo($dropdown);
                });
                $dropdown.appendTo($result);
            }
        });

        this._handleAttributes($result, node);
        this._registerModifiers(node, this.state, $result);
        return $result;
    },
    /**
    * @private
    * @returns {integer}
    */
    _renderButtonBoxNbButtons: function () {
        return [2, 2, 2, 4][config.device.size_class] || 7;
    },
    /**
     * Do not render a field widget if it is always invisible.
     *
     * @override
     */
    _renderFieldWidget(node) {
        if (!this.renderInvisible && node.attrs.modifiers.invisible === true) {
            return $();
        }
        return this._super(...arguments);
    },
    /**
     * @private
     * @param {Object} node
     * @returns {jQueryElement}
     */
    _renderGenericTag: function (node) {
        var $result = $('<' + node.tag + '>', _.omit(node.attrs, 'modifiers'));
        this._handleAttributes($result, node);
        this._registerModifiers(node, this.state, $result);
        $result.append(_.map(node.children, this._renderNode.bind(this)));
        return $result;
    },
    /**
     * @private
     * @param {Object} node
     * @returns {jQueryElement}
     */
    _renderHeaderButton: function (node) {
        var $button = viewUtils.renderButtonFromNode(node);

        // Current API of odoo for rendering buttons is "if classes are given
        // use those on top of the 'btn' and 'btn-{size}' classes, otherwise act
        // as if 'btn-secondary' class was given". The problem is that, for
        // header buttons only, we allowed users to only indicate their custom
        // classes without having to explicitely ask for the 'btn-secondary'
        // class to be added. We force it so here when no bootstrap btn type
        // class is found.
        if ($button.not('.btn-primary, .btn-secondary, .btn-link, .btn-success, .btn-info, .btn-warning, .btn-danger').length) {
            $button.addClass('btn-secondary');
        }

        this._addOnClickAction($button, node);
        this._handleAttributes($button, node);
        this._registerModifiers(node, this.state, $button);

        // Display tooltip
        if (config.isDebug() || node.attrs.help) {
            this._addButtonTooltip(node, $button);
        }
        return $button;
    },
    /**
     * @private
     * @param {Object} node
     * @returns {jQueryElement}
     */
    _renderHeaderButtons: function (node) {
        var self = this;
        var buttons = [];
        var children = [...node.children];
        while(children.length) {
            var child = children.shift();
            if (child.tag === 'button') {
                buttons.push(self._renderHeaderButton(child));
            }
            if (child.tag === 'widget') {
                buttons.push(self._renderTagWidget(child));
            }
            if (child.children){
                children.push(...child.children);
            }
        }
        return this._renderStatusbarButtons(buttons);
    },
    /**
     * @private
     * @param {Object} node
     * @returns {jQueryElement}
     */
    _renderInnerGroup: function (node) {
        var self = this;
        var $result = $('<table/>', {class: 'o_group o_inner_group'});
        var $tbody = $('<tbody />').appendTo($result);
        this._handleAttributes($result, node);
        this._registerModifiers(node, this.state, $result);

        var col = parseInt(node.attrs.col, 10) || this.INNER_GROUP_COL;

        if (node.attrs.string) {
            var $sep = $('<tr><td colspan="' + col + '" style="width: 100%;"><div class="o_horizontal_separator">' + node.attrs.string + '</div></td></tr>');
            $result.append($sep);
        }

        var rows = [];
        var $currentRow = $('<tr/>');
        var currentColspan = 0;
        node.children.forEach(function (child) {
            if (child.tag === 'newline') {
                rows.push($currentRow);
                $currentRow = $('<tr/>');
                currentColspan = 0;
                return;
            }

            var colspan = parseInt(child.attrs.colspan, 10);
            var isLabeledField = (child.tag === 'field' && child.attrs.nolabel !== '1');
            if (!colspan) {
                if (isLabeledField) {
                    colspan = 2;
                } else {
                    colspan = 1;
                }
            }
            var finalColspan = colspan - (isLabeledField ? 1 : 0);
            currentColspan += colspan;

            if (currentColspan > col) {
                rows.push($currentRow);
                $currentRow = $('<tr/>');
                currentColspan = colspan;
            }

            var $tds;
            if (child.tag === 'field') {
                $tds = self._renderInnerGroupField(child);
            } else if (child.tag === 'label') {
                $tds = self._renderInnerGroupLabel(child);
            } else {
                var $td = $('<td/>');
                var $child = self._renderNode(child);
                if ($child.hasClass('o_td_label')) { // transfer classname to outer td for css reasons
                    $td.addClass('o_td_label');
                    $child.removeClass('o_td_label');
                }
                $tds = $td.append($child);
            }
            if (finalColspan > 1) {
                $tds.last().attr('colspan', finalColspan);
            }
            $currentRow.append($tds);
        });
        rows.push($currentRow);

        _.each(rows, function ($tr) {
            var nonLabelColSize = 100 / (col - $tr.children('.o_td_label').length);
            _.each($tr.children(':not(.o_td_label)'), function (el) {
                var $el = $(el);
                $el.css('width', ((parseInt($el.attr('colspan'), 10) || 1) * nonLabelColSize) + '%');
            });
            $tbody.append($tr);
        });

        return $result;
    },
    /**
     * @private
     * @param {Object} node
     * @returns {jQueryElement}
     */
    _renderInnerGroupField: function (node) {
        var $el = this._renderFieldWidget(node, this.state);
        var $tds = $('<td/>').append($el);

        if (node.attrs.nolabel !== '1') {
            var $labelTd = this._renderInnerGroupLabel(node);
            $tds = $labelTd.add($tds);

            // apply the oe_(edit|read)_only className on the label as well
            if (/\boe_edit_only\b/.test(node.attrs.class)) {
                $tds.addClass('oe_edit_only');
            }
            if (/\boe_read_only\b/.test(node.attrs.class)) {
                $tds.addClass('oe_read_only');
            }
        }

        return $tds;
    },
    /**
     * @private
     * @param {Object} node
     * @returns {jQueryElement}
     */
    _renderInnerGroupLabel: function (node) {
        return $('<td/>', {class: 'o_td_label'})
            .append(this._renderTagLabel(node));
    },
    /**
     * Render a node, from the arch of the view. It is a generic method, that
     * will dispatch on specific other methods.  The rendering of a node is a
     * jQuery element (or a string), with the correct classes, attrs, and
     * content.
     *
     * For fields, it will return the $el of the field widget. Note that this
     * method is synchronous, field widgets are instantiated and appended, but
     * if they are asynchronous, they register their promises in this.defs, and
     * the _renderView method will properly wait.
     *
     * @private
     * @param {Object} node
     * @returns {jQueryElement | string}
     */
    _renderNode: function (node) {
        var renderer = this['_renderTag' + _.str.capitalize(node.tag)];
        if (renderer) {
            return renderer.call(this, node);
        }
        if (node.tag === 'div' && node.attrs.name === 'button_box') {
            return this._renderButtonBox(node);
        }
        if (_.isString(node)) {
            return node;
        }
        return this._renderGenericTag(node);
    },
    /**
     * Renders a 'group' node, which contains 'group' nodes in its children.
     *
     * @param {Object} node]
     * @returns {JQueryElement}
     */
    _renderOuterGroup: function (node) {
        var self = this;
        var $result = $('<div/>', {class: 'o_group'});
        var nbCols = parseInt(node.attrs.col, 10) || this.OUTER_GROUP_COL;
        var colSize = Math.max(1, Math.round(12 / nbCols));
        if (node.attrs.string) {
            var $sep = $('<div/>', {class: 'o_horizontal_separator'}).text(node.attrs.string);
            $result.append($sep);
        }
        $result.append(_.map(node.children, function (child) {
            if (child.tag === 'newline') {
                return $('<br/>');
            }
            var $child = self._renderNode(child);
            $child.addClass('o_group_col_' + (colSize * (parseInt(child.attrs.colspan, 10) || 1)));
            return $child;
        }));
        this._handleAttributes($result, node);
        this._registerModifiers(node, this.state, $result);
        return $result;
    },
    /**
     * @private
     * @param {Object} node
     * @returns {jQueryElement}
     */
    _renderStatButton: function (node) {
        var $button = viewUtils.renderButtonFromNode(node, {
            extraClass: 'oe_stat_button',
        });

        // If there is no type nor name, it will not bind a click listener and will set the button as disabled
        const buttonDoesStartAnAction = node.attrs.type || node.attrs.name;
        if (!buttonDoesStartAnAction) {
            $button[0].setAttribute("disabled", true);
        }

        $button.append(_.map(node.children, this._renderNode.bind(this)));
        if (node.attrs.help) {
            this._addButtonTooltip(node, $button);
        }
        if (buttonDoesStartAnAction) {
            this._addOnClickAction($button, node);
        }
        this._handleAttributes($button, node);
        this._registerModifiers(node, this.state, $button);
        return $button;
    },
    /**
     * @private
     * @param {Array} buttons
     * @return {jQueryElement}
     */
    _renderStatusbarButtons: function (buttons) {
        var $statusbarButtons = $('<div>', {class: 'o_statusbar_buttons'});
        buttons.forEach(button => $statusbarButtons.append(button));
        return $statusbarButtons;
    },
    /**
     * @private
     * @param {Object} page
     * @param {string} page_id
     * @returns {jQueryElement}
     */
    _renderTabHeader: function (page, page_id) {
        var $a = $('<a>', {
            'data-bs-toggle': 'tab',
            disable_anchor: 'true',
            href: '#' + page_id,
            class: 'nav-link',
            role: 'tab',
            text: page.attrs.string,
            name: page.attrs.name,
        });
        return $('<li>', {class: 'nav-item'}).append($a);
    },
    /**
     * @private
     * @param {Object} page
     * @param {string} page_id
     * @returns {jQueryElement}
     */
    _renderTabPage: function (page, page_id) {
        var $result = $('<div class="tab-pane" id="' + page_id + '">');
        $result.append(_.map(page.children, this._renderNode.bind(this)));
        return $result;
    },
    /**
     * @private
     * @param {Object} node
     * @returns {jQueryElement}
     */
    _renderTagButton: function (node) {
        var $button = viewUtils.renderButtonFromNode(node);
        $button.append(_.map(node.children, this._renderNode.bind(this)));
        this._addOnClickAction($button, node);
        this._handleAttributes($button, node);
        this._registerModifiers(node, this.state, $button);

        // Display tooltip
        if (config.isDebug() || node.attrs.help) {
            this._addButtonTooltip(node, $button);
        }

        return $button;
    },
    /**
     * @private
     * @param {Object} node
     * @returns {jQueryElement}
     */
    _renderTagField: function (node) {
        return this._renderFieldWidget(node, this.state);
    },
    /**
     * @private
     * @param {Object} node
     * @returns {jQueryElement}
     */
    _renderTagForm: function (node) {
        var $result = $('<div/>');
        if (node.attrs.class) {
            $result.addClass(node.attrs.class);
        }
        var allNodes = node.children.map(this._renderNode.bind(this));
        $result.append(allNodes);
        return $result;
    },
    /**
     * @private
     * @param {Object} node
     * @returns {jQueryElement}
     */
    _renderTagGroup: function (node) {
        var isOuterGroup = _.some(node.children, function (child) {
            return child.tag === 'group';
        });
        if (!isOuterGroup) {
            return this._renderInnerGroup(node);
        }
        return this._renderOuterGroup(node);
    },
    /**
     * @private
     * @param {Object} node
     * @returns {jQueryElement}
     */
    _renderTagHeader: function (node) {
        var self = this;
        var $statusbar = $('<div>', {class: 'o_form_statusbar'});
        $statusbar.append(this._renderHeaderButtons(node));
        _.each(node.children, function (child) {
            if (child.tag === 'field') {
                var $el = self._renderFieldWidget(child, self.state);
                $statusbar.append($el);
            }
        });
        this._handleAttributes($statusbar, node);
        this._registerModifiers(node, this.state, $statusbar);
        return $statusbar;
    },
    /**
     * @private
     * @param {Object} node
     * @returns {jQueryElement}
     */
    _renderTagLabel: function (node) {
        if (!this.renderInvisible && node.tag === 'field' &&
            node.attrs.modifiers.invisible === true) {
            // skip rendering of invisible fields/labels
            return $();
        }
        var self = this;
        var text;
        let fieldName;
        if (node.tag === 'label') {
            fieldName = this.fieldIdsToNames[node.attrs.for]; // 'for' references a <field> node id
        } else {
            fieldName = node.attrs.name;
        }
        if ('string' in node.attrs) { // allow empty string
            text = node.attrs.string;
        } else if (fieldName) {
            text = this.state.fields[fieldName].string;
        } else {
            return this._renderGenericTag(node);
        }
        var $result = $('<label>', {
            class: 'o_form_label',
            for: this._getIDForLabel(node.tag === 'label' ? node.attrs.for : node.attrs.id),
            text: text,
        });
        if (node.tag === 'label') {
            this._handleAttributes($result, node);
        }
        var modifiersOptions;
        if (fieldName) {
            modifiersOptions = {
                callback: function (element, modifiers, record) {
                    var widgets = self.allFieldWidgets[record.id];
                    var widget = _.findWhere(widgets, {name: fieldName});
                    const fieldsInfo = record.fieldsInfo[self.viewType];
                    if (!widget) {
                        if (fieldsInfo[fieldName]) {
                            self.labelsToPostProcess.push(element.callback.bind(self, element, modifiers, record));
                        }
                        return;
                    }
                    element.$el.toggleClass('o_form_label_empty', !!( // FIXME condition is evaluated twice (label AND widget...)
                        record.data.id
                        && (modifiers.readonly || self.mode === 'readonly')
                        && !widget.isSet()
                    ));
                },
            };
        }
        // FIXME if the function is called with a <label/> node, the registered
        // modifiers will be those on this node. Maybe the desired behavior
        // would be to merge them with associated field node if any... note:
        // this worked in 10.0 for "o_form_label_empty" reevaluation but not for
        // "o_invisible_modifier" reevaluation on labels...
        this._registerModifiers(node, this.state, $result, modifiersOptions);
        return $result;
    },
    /**
     * @private
     * @param {Object} node
     * @returns {jQueryElement}
     */
    _renderTagNotebook: function (node) {
        var self = this;
        var $headers = $('<ul class="nav nav-tabs">');
        var $pages = $('<div class="tab-content">');
        // renderedTabs is used to aggregate the generated $headers and $pages
        // alongside their node, so that their modifiers can be registered once
        // all tabs have been rendered, to ensure that the first visible tab
        // is correctly activated
        var renderedTabs = _.map(node.children, function (child, index) {
            var pageID = _.uniqueId('notebook_page_');
            var $header = self._renderTabHeader(child, pageID);
            var $page = self._renderTabPage(child, pageID);
            self._handleAttributes($header, child);
            $headers.append($header);
            $pages.append($page);
            return {
                $header: $header,
                $page: $page,
                node: child,
            };
        });
        // register the modifiers for each tab
        _.each(renderedTabs, function (tab) {
            self._registerModifiers(tab.node, self.state, tab.$header, {
                callback: function (element, modifiers) {
                    // if the active tab is invisible, activate the first visible tab instead
                    var $link = element.$el.find('.nav-link');
                    if (modifiers.invisible && $link.hasClass('active')) {
                        $link.removeClass('active');
                        tab.$page.removeClass('active');
                        self.inactiveNotebooks.push(renderedTabs);
                    }
                    if (!modifiers.invisible) {
                        // make first page active if there is only one page to display
                        var $visibleTabs = $headers.find('li:not(.o_invisible_modifier)');
                        if ($visibleTabs.length === 1) {
                            self.inactiveNotebooks.push(renderedTabs);
                        }
                    }
                    // if all pages are invisible then hide notebooks header's ul as well
                    $headers.toggleClass('o_invisible_modifier', !$headers.find('li:not(.o_invisible_modifier)').length);
                },
            });
        });
        this._activateFirstVisibleTab(renderedTabs);
        var $notebookHeaders = $('<div class="o_notebook_headers">').append($headers);
        var $notebook = $('<div class="o_notebook">').append($notebookHeaders, $pages);
        $notebook[0].dataset.name = node.attrs.name || '_default_';
        this._registerModifiers(node, this.state, $notebook);
        this._handleAttributes($notebook, node);
        return $notebook;
    },
    /**
     * @private
     * @param {Object} node
     * @returns {jQueryElement}
     */
    _renderTagSeparator: function (node) {
        var $separator = $('<div/>').addClass('o_horizontal_separator').text(node.attrs.string);
        this._handleAttributes($separator, node);
        this._registerModifiers(node, this.state, $separator);
        return $separator;
    },
    /**
     * @private
     * @param {Object} node
     * @returns {jQueryElement}
     */
    _renderTagSheet: function (node) {
        this.has_sheet = true;
        var $sheet = $('<div>', {class: 'clearfix position-relative o_form_sheet'});
        $sheet.append(node.children.map(this._renderNode.bind(this)));
        return $sheet;
    },
    /**
     * Instantiate custom widgets
     *
     * @private
     * @param {Object} node
     * @returns {jQueryElement}
     */
    _renderTagWidget: function (node) {
        return this._renderWidget(this.state, node);
    },
    /**
     * Main entry point for the rendering.  From here, we call _renderNode on
     * the root of the arch, then, when every promise (from the field widgets)
     * are done, it will resolves itself.
     *
     * @private
     * @override method from BasicRenderer
     * @returns {Promise}
     */
    _renderView: function () {
        var self = this;

        // render the form and evaluate the modifiers
        var defs = [];
        this.defs = defs;
        this.inactiveNotebooks = [];
        var $form = this._renderNode(this.arch).addClass(this.className);
        delete this.defs;

        return Promise.all(defs).then(() => this.__renderView()).then(function () {
            self._postProcessLabels();
            self._updateView($form.contents());
            self.manuallyDisabledButtons.clear();
            if (self.state.res_id in self.alertFields) {
                self.displayTranslationAlert();
            }
        }).then(function(){
            if (self.lastActivatedFieldIndex >= 0) {
                self._activateNextFieldWidget(self.state, self.lastActivatedFieldIndex);
            }
        }).guardedCatch(function () {
            $form.remove();
        });
    },
    /**
     * Meant to be overridden if asynchronous work needs to be done when
     * rendering the view. This is called right before attaching the new view
     * content.
     * @private
     * @returns {Promise<any>}
     */
    async __renderView() {},
    /**
     * This method is overridden to activate the first notebook page if the
     * current active page is invisible due to modifiers. This is done after
     * all modifiers are applied on all page elements.
     *
     * @override
     */
    async _updateAllModifiers() {
        await this._super(...arguments);
        for (const tabs of this.inactiveNotebooks) {
            this._activateFirstVisibleTab(tabs);
        }
        this.inactiveNotebooks = [];
    },
    /**
     * Updates the form's $el with new content.
     *
     * @private
     * @see _renderView
     * @param {JQuery} $newContent
     */
    _updateView: function ($newContent) {
        var self = this;

        // Set the new content of the form view, and toggle classnames
        this.$el.html($newContent);
        this.$el.toggleClass('o_form_nosheet', !this.has_sheet);
        if (this.has_sheet) {
            this.$el.children().not('.o_FormRenderer_chatterContainer')
                .wrapAll($('<div/>', {class: 'o_form_sheet_bg', 'data-command-category': "app"}));
        }
        this.$el.toggleClass('o_form_editable', this.mode === 'edit');
        this.$el.toggleClass('o_form_readonly', this.mode === 'readonly');

        // Attach the tooltips on the fields' label
        _.each(this.allFieldWidgets[this.state.id], function (widget) {
            const idForLabel = self.idsForLabels[widget[symbol]];
            var $label = idForLabel ? self.$('.o_form_label[for=' + idForLabel + ']') : $();
            self._addFieldTooltip(widget, $label);
            if (widget.attrs.widget === 'upgrade_boolean') {
                // this widget needs a reference to its $label to be correctly
                // rendered
                widget.renderWithLabel($label);
            }
        });
    },
    /**
     * Sets id attribute of given widget to idForLabel
     *
     * @private
     * @param {AbstractField} widget
     * @param {idForLabel} string
     */
    _setIDForLabel: function (widget, idForLabel) {
        widget.setIDForLabel(idForLabel);
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {OdooEvent} ev
     */
    _onActivateNextWidget: function (ev) {
        ev.stopPropagation();
        var index = this.allFieldWidgets[this.state.id].indexOf(ev.data.target);
        this._activateNextFieldWidget(this.state, index);
    },
    /**
     * Ensure that the pane containing an anchor `element` that has been
     * targeted by a link will be visible in a notebook.
     * @param {CustomEvent} ev
     * @param {object} ev[detail] payload containing the element and the id to look for
     * 
     */
    _onAnchorLinkClicked(ev) {
        // Todo: we might need to search for the element elsewhere to know wich tab to activate
        // Maybe a t-if rule is hidding the target from the DOM
        const anchor = ev.detail.element || null;
        if (!anchor) {
            return;
        }
        function _getNotebookParent() {
            const notebook = anchor.closest(".o_notebook");
            // If the notebook is containing the element, return the notebook
            return notebook && notebook.contains(anchor) ? notebook : null;
        }
        function _setNotebookPage() {
            // Simulate a click on the nav link corresponding to the target pane
            const parentPane = anchor.closest(".tab-pane");
            if (notebook.contains(parentPane) && !parentPane.classList.contains(".active")) {
                const navLink = [...notebook.querySelectorAll(".nav-link")].filter((e) =>
                    e.href.includes(parentPane.id)
                );
                navLink[0].click();
            }
        }
        
        const notebook = _getNotebookParent();

        // If the element is contained in a notebook, the page must be visible
        if (notebook) {
            _setNotebookPage();
            // Prevent the scroll to be handled by the scroller service itself
            ev.preventDefault();
            ev.detail.originalEv.preventDefault();
            scrollUtils.scrollTo(ev.detail.element, { isAnchor: true });
        }
    },
    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onFieldLabelClicked: function (ev) {
        const idForLabel = ev.currentTarget.getAttribute('for');
        const entry = Object.entries(this.idsForLabels)
            .find(x => x[1] === idForLabel);
        if (entry) {
            this.trigger_up('quick_edit', {
                fieldName: this.fieldIdsToNames[entry[0]],
                target: ev.currentTarget,
                extraInfo: {},
            });
        }
    },
    /**
     * @override
     * @private
     * @param {OdooEvent} ev
     */
    _onNavigationMove: function (ev) {
        ev.stopPropagation();
        // We prevent the default behaviour and stop the propagation of the
        // originalEvent when the originalEvent is a tab keydown to not let
        // the browser do it. The action is done by this renderer.
        if (ev.data.originalEvent && ['next', 'previous'].includes(ev.data.direction)) {
            ev.data.originalEvent.preventDefault();
            ev.data.originalEvent.stopPropagation();
        }
        if (["next", "previous"].includes(ev.data.direction)) {
            const fieldWidgets = this.allFieldWidgets[this.state.id];
            let target = ev.data.target || ev.target;
            let index;
            if (target.__owl__) {
                // the fieldWidget is an owl component, so we need to find the
                // FieldWrapper that wraps the owl component that triggered the event
                index = fieldWidgets.findIndex((widget) => {
                    return widget.componentRef && widget.componentRef.comp === target;
                });
            } else {
                index = fieldWidgets.indexOf(target);
            }
            if (ev.data.direction === "next") {
                this._activateNextFieldWidget(this.state, index);
            } else if (ev.data.direction === "previous") {
                this._activatePreviousFieldWidget(this.state, index);
            }
        }
    },
    /**
     * Listen to notebook tab changes and trigger a DOM_updated event such that
     * widgets in the visible tab can correctly compute their dimensions (e.g.
     * autoresize on field text)
     *
     * @private
     */
    _onNotebookTabChanged: function () {
        core.bus.trigger('DOM_updated');
    },
    /**
     * @private
     * @param {OdooEvent} ev
     */
    _onQuickEdit: function (ev) {
        if (this.mode !== 'readonly' ||
            this.quickEditExclusion.some(x => ev.data.target.closest(x))
        ) {
            ev.stopPropagation();
        }
    },
    /**
     * open the translation view for the current field
     *
     * @private
     * @param {MouseEvent} ev
     */
    _onTranslate: function (ev) {
        ev.preventDefault();
        this.trigger_up('translate', {
            fieldName: ev.target.name,
            id: this.state.id,
            isComingFromTranslationAlert: true,
        });
    },
    /**
     * remove alert fields of record from alertFields object
     *
     * @private
     * @param {MouseEvent} ev
     */
    _onTranslateNotificationClose: function(ev) {
        const notificationElement = this.el.querySelector('.o_notification_box');
        Alert.getOrCreateInstance(notificationElement).close();
        delete this.alertFields[this.state.res_id];
    },
});

return FormRenderer;
});
