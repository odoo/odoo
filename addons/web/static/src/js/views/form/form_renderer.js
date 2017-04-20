odoo.define('web.FormRenderer', function (require) {
"use strict";

var BasicRenderer = require('web.BasicRenderer');
var config = require('web.config');
var core = require('web.core');

var _t = core._t;
var qweb = core.qweb;

var FIELD_CLASSES = {
    'one2many': 'o_field_one2many',
};

var FormRenderer = BasicRenderer.extend({
    className: "o_form_view",
    /**
     * @override
     */
    init: function (parent, state, params) {
        this._super.apply(this, arguments);
        this.idsForLabels = {};
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Extend the method so that labels also receive the 'o_form_invalid' class
     * if necessary.
     *
     * @override
     * @see BasicRenderer.canBeSaved
     * @param {string} recordID
     * @returns {string[]}
     */
    canBeSaved: function (recordID) {
        var self = this;
        var fieldNames = this._super.apply(this, arguments);

        var $labels = this.$('label');
        $labels.removeClass('o_form_invalid');

        _.each(fieldNames, function (fieldName) {
            var idForLabel = self.idsForLabels[fieldName];
            if (idForLabel) {
                $labels
                    .filter('[for=' + idForLabel + ']')
                    .addClass('o_form_invalid');
            }
        });
        return fieldNames;
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
        var state = {};
        this.$('div.o_notebook').each(function () {
            var $notebook = $(this);
            var name = $notebook.data('name');
            var index = -1;
            $notebook.find('li').each(function (i) {
                if ($(this).hasClass('active')) {
                    index = i;
                }
            });
            state[name] = index;
        });
        return state;
    },
    /**
     * restore active tab pages for each notebook
     *
     * @todo make sure this method is called
     *
     * @param {Object} state the result from a getLocalState call
     */
    setLocalState: function (state) {
        this.$('div.o_notebook').each(function () {
            var $notebook = $(this);
            var name = $notebook.data('name');
            if (name in state) {
                var $page = $notebook.find('> ul > li').eq(state[name]);
                if (!$page.hasClass('o_form_invisible')) {
                    $page.find('a[data-toggle="tab"]').click();
                }
            }
        });
    },
    /**
     * @override method from AbstractRenderer
     * @param {Object} state a valid state given by the model
     * @param {Object} params
     * @param {string} [params.mode] new mode, either 'edit' or 'readonly'
     * @param {string[]} [params.fieldNames] if given, the renderer will only
     *   update the fields in this list
     * @returns {Deferred}
     */
    updateState: function (state, params) {
        this.mode = (params && 'mode' in params) ? params.mode : this.mode;

        // if fieldNames are given, we update the corresponding field widget.
        // I think this is wrong, and the caller could directly call the
        // confirmChange method
        if (params.fieldNames) {
            // only update the given fields
            return this.confirmChange(state, state.id, params.fieldNames);
        }
        return this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Adds the adequate classnames to a field widget's $el.
     *
     * @private
     * @param {Object} widget a field widget
     */
    _addFieldClassNames: function (widget) {
        widget.$el.addClass('o_form_field'); // TODO will be removed in the CSS update
    },
    /**
     * @private
     * @param {jQueryElement} $el
     * @param {Object} node
     */
    _addOnClickAction: function ($el, node) {
        var self = this;
        $el.click(function () {
            self.trigger_up('button_clicked', {
                attrs: node.attrs,
                record: self.state,
                show_wow: self.$el.hasClass('o_wow'),  // TODO: implement this (in view)
            });
        });
    },
    /**
     * @private
     * @param {string} name
     * @returns {string}
     */
    _getIDForLabel: function (name) {
        var idForLabel = this.idsForLabels[name];
        if (!idForLabel) {
            idForLabel = _.uniqueId('o_field_input_');
            this.idsForLabels[name] = idForLabel;
        }
        return idForLabel;
    },
    /**
     * @private
     * @param {jQueryElement} $el
     * @param {Object} node
     */
    _handleAttributes: function ($el, node) {
        if (node.attrs.class) {
            $el.addClass(node.attrs.class);
        }
        if (node.attrs.style) {
            $el.attr('style', node.attrs.style);
        }
    },
    /**
     * @private
     * @param {Object} node
     * @returns {jQueryElement}
     */
    _renderButtonBox: function (node) {
        var self = this;
        var $result = $('<' + node.tag + '>', { 'class': 'o_not_full' });
        // Avoid to show buttons if we are in create mode (edit mode without res_id)
        if (this.mode === 'edit' && !this.state.res_id) {
            return $result;
        }
        var buttons = _.map(node.children, function (child) {
            if (child.tag === 'button') {
                return self._renderStatButton(child);
            } else {
                return self._renderNode(child);
            }
        });
        var buttons_partition = _.partition(buttons, function ($button) {
            return $button.is('.o_form_invisible');
        });
        var invisible_buttons = buttons_partition[0];
        var visible_buttons = buttons_partition[1];

        // Get the unfolded buttons according to window size
        var nb_buttons = [2, 4, 6, 7][config.device.size_class];
        var unfolded_buttons = visible_buttons.slice(0, nb_buttons).concat(invisible_buttons);

        // Get the folded buttons
        var folded_buttons = visible_buttons.slice(nb_buttons);
        if (folded_buttons.length === 1) {
            unfolded_buttons = buttons;
            folded_buttons = [];
        }

        // Toggle class to tell if the button box is full (LESS requirement)
        var full = (visible_buttons.length > nb_buttons);
        $result.toggleClass('o_full', full).toggleClass('o_not_full', !full);

        // Add the unfolded buttons
        _.each(unfolded_buttons, function ($button) {
            $button.appendTo($result);
        });

        // Add the dropdown with folded buttons if any
        if (folded_buttons.length) {
            $result.append($("<button>", {
                type: 'button',
                'class': "btn btn-sm oe_stat_button o_button_more dropdown-toggle",
                'data-toggle': "dropdown",
                text: _t("More"),
            }));

            var $ul = $("<ul>", {'class': "dropdown-menu o_dropdown_more", role: "menu"});
            _.each(folded_buttons, function ($button) {
                $('<li>').appendTo($ul).append($button);
            });
            $ul.appendTo($result);
        }

        this._handleAttributes($result, node);
        this._registerModifiers(node, this.state, $result);
        return $result;
    },
    /**
     * @override
     * @private
     * @param {string} node
     * @param {Object} record
     * @param {Object} [options]
     * @returns {AbstractField}
     */
    _renderFieldWidget: function (node, record, options, modifiersOptions) {
        var self = this;
        modifiersOptions = _.extend({
            callback: function (element, modifiers, record) {
                element.$el.toggleClass('o_form_field_empty', !!( // FIXME condition is evaluated twice (label AND widget...)
                    record.data.id
                    && (modifiers.readonly || self.mode === 'readonly')
                    && !element.widget.isSet()
                ));
            },
        }, modifiersOptions || {});

        var widget = this._super(node, record, options, modifiersOptions);
        widget.getFocusableElement().attr('id', this._getIDForLabel(node.attrs.name));

        widget.$el.addClass(FIELD_CLASSES[record.fields[node.attrs.name].type]);
        this._addFieldClassNames(widget);
        this._handleAttributes(widget.$el, node);
        if (JSON.parse(node.attrs.default_focus || "0")) {
            this.defaultFocusField = widget;
        }
        return widget;
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
        var $button = $('<button>')
                        .text(node.attrs.string)
                        .addClass('btn btn-sm btn-default');
        this._addOnClickAction($button, node);
        this._handleAttributes($button, node);
        this._registerModifiers(node, this.state, $button);
        return $button;
    },
    /**
     * @private
     * @param {Object} node
     * @returns {jQueryElement}
     */
    _renderHeaderButtons: function (node) {
        var self = this;
        var $buttons = $('<div>', {class: 'o_statusbar_buttons'});
        _.each(node.children, function (child) {
            if (child.tag === 'button') {
                $buttons.append(self._renderHeaderButton(child));
            }
        });
        return $buttons;
    },
    /**
     * @private
     * @param {Object} node
     * @returns {jQueryElement}
     */
    _renderInnerField: function (node) {
        var self = this;
        var fieldName = node.attrs.name;
        var field = this.state.fields[fieldName];
        var fieldDescr = node.attrs.string || field.string;
        var widget = this._renderFieldWidget(node, this.state);

        if (!node.attrs.nolabel) {
            var $label = $('<label>', {
                class: 'o_form_label',
                for: this._getIDForLabel(node.attrs.name),
                text: fieldDescr,
            });
            this._registerModifiers(node, this.state, $label, {
                callback: function (element, modifiers, record) {
                    element.$el.toggleClass('o_form_label_empty', !!(
                        record.data.id
                        && (modifiers.readonly || self.mode === 'readonly')
                        && !widget.isSet() // getting like this because it could have been re-rendered...
                    ));
                },
            });
            return $('<tr>')
                    .append($('<td class="o_td_label">').append($label))
                    .append($('<td style="width: 100%">').append(widget.$el));
        } else {
            var style = {
                width: 100/2 + '%',
            };
            return $('<tr>')
                    .append($('<td colspan="1">').css(style).append(widget.$el));
        }
    },
    /**
     * @private
     * @param {Object} node
     * @returns {jQueryElement}
     */
    _renderInnerGroup: function (node) {
        var $result = $('<table class="o_group o_inner_group"/>');
        this._handleAttributes($result, node);
        this._registerModifiers(node, this.state, $result);
        if (node.attrs.string) {
            var $sep = $('<tr><td colspan="2" style="width:100%;"><div class="o_horizontal_separator">' + node.attrs.string + '</div></td></tr>');
            $result.append($sep);
        }
        var children = node.children;
        for (var i = 0; i < children.length; i++) {
            if (children[i].tag === 'field') {
                var fieldNodes = [children[i]];
                if (children[i].attrs.nolabel && children[i+1] &&
                        children[i+1].tag === 'field' && children[i+1].attrs.nolabel) {
                    fieldNodes.push(children[i+1]);
                    i++;
                }
                $result.append(this._renderInnerGroupRow(fieldNodes));
            } else if (children[i].tag === 'label') {
                var label =  children[i];
                // If there is a "for" attribute, we expect to have an id concerned in the next node.
                if (label.attrs.for) {
                    var linkedNode = children[i+1];
                    $result = this._renderInnerGroupLabel($result, label, linkedNode);
                    i++; // Skip the rendering of the next node because we just did it.
                } else {
                    $result = this._renderInnerGroupLabel($result, label);
                }
            } else {
                var $td = $('<td colspan="2" style="width:100%;">').append(this._renderNode(children[i]));
                $result.append($('<tr>').append($td));
            }
        }
        return $result;
    },
    /**
     * @private
     * @param {jQueryElement} $result
     * @param {string} label
     * @param {Object} linkedNode
     * @returns {jQueryElement}
     */
    _renderInnerGroupLabel: function ($result, label, linkedNode) {
        var $first = $('<td class="o_td_label">')
                    .append(this._renderNode(label));
        var $second = linkedNode ? $('<td>').append(this._renderNode(linkedNode)) : $('<td>');
        var $tr = $('<tr>').append($first).append($second);
        return $result.append($tr);
    },
    /**
     * Render a group row, with all the nodes inside.
     *
     * @private
     * @param {Object[]} nodes
     * @returns {jQueryElement}
     */
    _renderInnerGroupRow: function (nodes) {
        var $tr = $('<tr>');
        for (var i = 0; i < nodes.length; i++) {
            $tr.append(this._renderInnerField(nodes[i]).contents());
        }
        return $tr;
    },
    /**
     * Render a node, from the arch of the view. It is a generic method, that
     * will dispatch on specific other methods.  The rendering of a node is a
     * jQuery element (or a string), with the correct classes, attrs, and
     * content.
     *
     * For fields, it will return the $el of the field widget. Note that this
     * method is synchronous, field widgets are instantiated and appended, but
     * if they are asynchronous, they register their deferred in this.defs, and
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
     * @private
     * @param {Object} node
     * @returns {jQueryElement}
     */
    _renderStatButton: function (node) {
        var $button = $('<button>').addClass('btn btn-sm oe_stat_button');
        if (node.attrs.icon) {
            $('<div>')
                .addClass('fa fa-fw o_button_icon')
                .addClass(node.attrs.icon)
                .appendTo($button);
        }
        if (node.attrs.string) {
            $('<span>')
                .text(node.attrs.string)
                .appendTo($button);
        }
        $button.append(_.map(node.children, this._renderNode.bind(this)));
        this._addOnClickAction($button, node);
        this._handleAttributes($button, node);
        this._registerModifiers(node, this.state, $button);
        return $button;
    },
    /**
     * @private
     * @param {Object} page
     * @param {string} page_id
     * @returns {jQueryElement}
     */
    _renderTabHeader: function (page, page_id) {
        var $a = $('<a>', {
            'data-toggle': 'tab',
            disable_anchor: 'true',
            href: '#' + page_id,
            role: 'tab',
            text: page.attrs.string,
        });
        return $('<li>').append($a);
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
        var widget = {
            node: node,
            string: (node.attrs.string || '').replace(/_/g, '')
        };
        if (node.attrs.icon) {
            widget.fa_icon = node.attrs.icon.indexOf('fa-') === 0;
        }
        var $button = $(qweb.render('WidgetButton', {widget: widget}));
        $button.append(_.map(node.children, this._renderNode.bind(this)));
        this._addOnClickAction($button, node);
        this._handleAttributes($button, node);
        this._registerModifiers(node, this.state, $button);
        return $button;
    },
    /**
     * @private
     * @param {Object} node
     * @returns {jQueryElement}
     */
    _renderTagField: function (node) {
        return this._renderFieldWidget(node, this.state).$el;
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
        $result.append(_.map(node.children, this._renderNode.bind(this)));
        return $result;
    },
    /**
     * @private
     * @param {Object} node
     * @returns {jQueryElement}
     */
    _renderTagGroup: function (node) {
        var self = this;
        var isOuterGroup = _.some(node.children, function (child) {
            return child.tag === 'group';
        });
        if (!isOuterGroup) {
            return this._renderInnerGroup(node);
        }

        var $result = $('<div class="o_group"/>');
        var $child;
        _.each(node.children, function (child) {
            if (child.tag === 'group') {
                $child = self._renderInnerGroup(child);
            } else {
                $child = self._renderNode(child);
            }
            $child.addClass('o_group_col_6');
            $child.appendTo($result);
        });
        this._handleAttributes($result, node);
        this._registerModifiers(node, this.state, $result);
        return $result;
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
                var widget = self._renderFieldWidget(child, self.state);
                $statusbar.append(widget.$el);
            }
        });
        return $statusbar;
    },
    /**
     * @private
     * @param {Object} node
     * @returns {jQueryElement}
     */
    _renderTagLabel: function (node) {
        var text;
        if ('string' in node.attrs) { // allow empty string
            text = node.attrs.string;
        } else if (node.attrs.for) {
            text = this.state.fields[node.attrs.for].string;
        } else  {
            return this._renderGenericTag(node);
        }
        var $result = $('<label>')
                        .addClass('o_form_label')
                        .attr('for', this._getIDForLabel(node.attrs.for))
                        .text(text);
        this._handleAttributes($result, node);
        this._registerModifiers(node, this.state, $result);
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
        var $pages = $('<div class="tab-content nav nav-tabs">');
        // renderedTabs is used to aggregate the generated $headers and $pages
        // alongside their node, so that their modifiers can be registered once
        // all tabs have been rendered, to ensure that the first visible tab
        // is correctly activated
        var renderedTabs = _.map(node.children, function (child, index) {
            var pageID = _.uniqueId('notebook_page_');
            var $header = self._renderTabHeader(child, pageID);
            var $page = self._renderTabPage(child, pageID);
            if (index === 0) {
                $header.addClass('active');
                $page.addClass('active');
            }
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
                    if (modifiers.invisible && element.$el.hasClass('active')) {
                        element.$el.removeClass('active');
                        tab.$page.removeClass('active');
                        var $firstVisibleTab = $headers.find('li:not(.o_form_invisible):first()');
                        $firstVisibleTab.addClass('active');
                        $pages.find($firstVisibleTab.find('a').attr('href')).addClass('active');
                    }
                },
            });
        });
        return $('<div class="o_notebook">')
                .data('name', node.attrs.name || '_default_')
                .append($headers)
                .append($pages);
    },
    /**
     * @private
     * @param {Object} node
     * @returns {jQueryElement}
     */
    _renderTagSeparator: function (node) {
        return $('<div/>').addClass('o_horizontal_separator').text(node.attrs.string);
    },
    /**
     * @private
     * @param {Object} node
     * @returns {jQueryElement}
     */
    _renderTagSheet: function (node) {
        this.has_sheet = true;
        var $result = $('<div>').addClass('o_form_sheet_bg');
        var $sheet = $('<div>').addClass('o_form_sheet');
        $sheet.append(_.map(node.children, this._renderNode.bind(this)));
        $result.append($sheet);
        return $result;
    },
    /**
     * Main entry point for the rendering.  From here, we call _renderNode on
     * the root of the arch, then, when every deferred (from the field widgets)
     * are done, it will resolves itself.
     *
     * @private
     * @override method from BasicRenderer
     * @returns {Deferred}
     */
    _renderView: function () {
        var self = this;

        // render the form and evaluate the modifiers
        var defs = [];
        this.defs = defs;
        var $form = this._renderNode(this.arch).addClass(this.className);
        delete this.defs;

        return $.when.apply($, defs).then(function () {
            self._updateView($form.contents());
        });
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
        this.$el.toggleClass('o_form_editable', this.mode === 'edit');
        this.$el.toggleClass('o_form_readonly', this.mode === 'readonly');

        // Necessary to allow all sub widgets to use their dimensions in
        // layout related activities, such as autoresize on fieldtexts
        core.bus.trigger('DOM_updated');

        // Attach the tooltips on the fields' label
        var focusWidget = this.defaultFocusField;
        _.each(this.allFieldWidgets[this.state.id], function (widget) {
            if (!focusWidget) {
                focusWidget = widget;
            }
            if (core.debug || widget.attrs.help || widget.field.help) {
                var idForLabel = self.idsForLabels[widget.name];
                var $label = idForLabel ? self.$('label[for=' + idForLabel + ']') : $();
                self._addFieldTooltip(widget, $label);
            }
        });
        if (focusWidget) {
            focusWidget.activate(true);
        }
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @override
     * @private
     * @param {OdooEvent} ev
     */
    _onMoveNext: function (ev) {
        ev.stopPropagation();
        var index = this.allFieldWidgets[this.state.id].indexOf(ev.target);
        this._activateNextFieldWidget(this.state, index);
    },
    /**
     * @override
     * @private
     * @param {OdooEvent} event
     */
    _onMovePrevious: function (ev) {
        ev.stopPropagation();
        var index = this.allFieldWidgets[this.state.id].indexOf(ev.target);
        this._activatePreviousFieldWidget(this.state, index);
    },
});

return FormRenderer;
});
