odoo.define('web.FormRenderer', function (require) {
"use strict";

var BasicRenderer = require('web.BasicRenderer');
var config = require('web.config');
var core = require('web.core');
var Domain = require('web.Domain');

var _t = core._t;
var qweb = core.qweb;

var FIELD_CLASSES = {
    'one2many': 'o_field_one2many',
};

return BasicRenderer.extend({
    className: "o_form_view",
    /**
     * @override method from BasicRenderer
     * @param {Object} params
     * @param {string} params.mode either 'readonly' on 'edit'
     */
    init: function (parent, state, params) {
        this._super.apply(this, arguments);
        this.idsForLabels = {};
        this.widgets = [];
        this.mode = params.mode;
        this.field_values = this._getFieldValues(this.state);
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * This method has two responsabilities: find every invalid fields in the
     * current form, and making sure that they are displayed as invalid, by
     * toggling the o_form_invalid css class.  It has to be done both on the
     * widget, and on the label, if there is a label.
     *
     * @returns {string[]} the list of invalid field names
     */
    checkInvalidFields: function () {
        var self = this;
        var invalid_fields = [];
        _.each(this.widgets, function (widget) {
            var is_valid = widget.isValid();
            if (!is_valid) {
                invalid_fields.push(widget.name);
            }
            widget.$el.toggleClass('o_form_invalid', !is_valid);
            var idForLabel = self.idsForLabels[widget.name];
            var $label = idForLabel ? self.$('label[for=' + idForLabel + ']') : $();
            $label.toggleClass('o_form_invalid', !is_valid);
        });
        return invalid_fields;
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
                $notebook.find('> ul > li > a[data-toggle="tab"]')
                         .eq(state[name])
                         .click();
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
        // updateWidgets method
        if (params.fieldNames) {
            // only update the given fields
            return this.updateWidgets(params.fieldNames, state);
        }
        this.field_values = this._getFieldValues(state);
        return this._super.apply(this, arguments);
    },
    /**
     * Update some field widgets with a new state.  We could rerender the form
     * view from scratch, but then it would not be as efficient, and we might
     * lose some local state, such as the input focus cursor, or the scrolling
     * position.
     *
     * @param {string[]} fields list of fields to be updated
     * @param {Object} state new state
     * @param {OdooEvent} [event] the event that triggered the change
     * @returns {Deferred}
     */
    updateWidgets: function (fields, state, event) {
        this.state = state;
        this.field_values = this._getFieldValues(this.state);
        var defs = [];
        _.each(this.widgets, function (widget) {
            if (_.contains(fields, widget.name) || widget.resetOnAnyFieldChange) {
                defs.push(widget.reset(state, event));
            }
        });
        // re-evalute the modifiers with the new state
        this._evaluateModifiers();
        return $.when.apply($, defs);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Adds the adequate classnames to a field widget's $el.
     *
     * @param {Object} widget a field widget
     * @param {Object} field description of the field
     */
    _addFieldClassNames: function (widget, field) {
        widget.$el.addClass('o_form_field');
        // classname 'o_form_field_empty' hides the widget, so we apply it in
        // on existing records for fields with no value, in readonly mode or if the
        // field is readonly
        if (this.state.data.id && !widget.isSet() && (this.mode === 'readonly' || field.readonly)) {
            widget.$el.addClass('o_form_field_empty');
        }
    },
    _addOnClickAction: function ($el, node) {
        var self = this;
        $el.click(function () {
            self.trigger_up('button_clicked', {
                attrs: node.attrs,
                record: this.state,
                show_wow: self.$el.hasClass('o_wow'),  // TODO: implement this (in view)
            });
        });
    },
    _evaluateModifiers: function () {
        var self = this;
        _.each(this.nodeModifiers, function (d) {
            if ('invisible' in d.modifiers) {
                var is_invisible = new Domain(d.modifiers.invisible).compute(self.field_values);
                d.$el.toggleClass('o_form_invisible', is_invisible);
                if (d.onEvalCallback) {
                    d.onEvalCallback({invisible: is_invisible});
                }
            }
        });
    },
    _getIDForLabel: function (name) {
        var idForLabel = this.idsForLabels[name];
        if (!idForLabel) {
            idForLabel = _.uniqueId('o_field_input_');
            this.idsForLabels[name] = idForLabel;
        }
        return idForLabel;
    },
    _handleAttributes: function ($el, node, onEvalCallback) {
        // register the modifiers with their corresponding $el so that they can
        // be re-evaluated at each field changed
        this.nodeModifiers.push({
            $el: $el,
            modifiers: JSON.parse(node.attrs.modifiers || "{}"),
            onEvalCallback: onEvalCallback,
        });
        if (node.attrs.class) {
            $el.addClass(node.attrs.class);
        }
    },
    _renderButtonBox: function (node) {
        var $result = $('<' + node.tag + '>', { 'class': 'o_not_full' });
        // Avoid to show buttons if we are in create mode (edit mode without res_id)
        if (this.mode === 'edit' && !this.state.res_id) {
            return $result;
        }
        var buttons = _.map(node.children, this._renderStatButton.bind(this));
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
        if(folded_buttons.length === 1) {
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
        if(folded_buttons.length) {
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
        return $result;
    },
    _renderFieldWidget: function (node) {
        var name = node.attrs.name;
        var field = this.state.fields[name];

        var modifiers = JSON.parse(node.attrs.modifiers || "{}");
        var is_readonly = new Domain(modifiers.readonly).compute(this.field_values);
        var is_required = field.required || new Domain(modifiers.required).compute(this.field_values);
        var options = {
            mode: is_readonly ? 'readonly' : this.mode,
            required: is_required,
            idForLabel: this._getIDForLabel(name),
        };
        var widget = new this.state.fieldAttrs[name].Widget(this, name, this.state, options);
        this.widgets.push(widget);
        var def = widget.__widgetRenderAndInsert(function () {});
        if (def.state() === 'pending') {
            this.defs.push(def);
        }
        widget.$el.addClass(FIELD_CLASSES[field.type]);
        this._handleAttributes(widget.$el, node);
        this._addFieldClassNames(widget, field);

        return widget;
    },
    _renderGenericTag: function (node) {
        var $result = $('<' + node.tag + '>');
        _.each(node.attrs, function (attr, name) {
            if (name !== 'class' && name !== 'modifiers') {
                $result.attr(name, attr);
            }
        });
        this._handleAttributes($result, node);
        $result.append(_.map(node.children, this._renderNode.bind(this)));
        return $result;
    },
    _renderHeaderButton: function (node) {
        var $button = $('<button>')
                        .text(node.attrs.string)
                        .addClass('btn btn-sm btn-default');
        this._addOnClickAction($button, node);
        this._handleAttributes($button, node);
        return $button;
    },
    _renderInnerField: function (node) {
        var field = this.state.fields[node.attrs.name];
        var fieldDescr = node.attrs.string || field.string;
        var hasLabel = !node.attrs.nolabel;
        var widget = this._renderFieldWidget(node);
        if (hasLabel) {
            var $label = $('<label>')
                            .addClass('o_form_label')
                            .attr('for', this._getIDForLabel(node.attrs.name))
                            .text(fieldDescr);
            var isReadOnly = this.mode === 'readonly' || field.readonly;
            if (this.state.data.id && !widget.isSet() && isReadOnly) {
                $label.addClass('o_form_label_empty');
            }
            this._handleAttributes($label, node);
            return $('<tr>')
                    .append($('<td class="o_td_label">').append($label))
                    .append($('<td style="width: 100%">').append(widget.$el));
        } else {
            var style = {
                width: 100/2 + '%'
            };
            return $('<tr>')
                    .append($('<td colspan="1">').css(style).append(widget.$el));
        }
    },
    _renderInnerGroup: function (node) {
        var $result = $('<table class="o_group o_inner_group"/>');
        this._handleAttributes($result, node);
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
                $result = this._renderInnerGroupRow($result, fieldNodes);
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
    _renderInnerGroupLabel: function ($result, label, linkedNode) {
        var $first = $('<td class="o_td_label">')
                    .append(this._renderNode(label));
        var $second = linkedNode ? $('<td>').append(this._renderNode(linkedNode)) : $('<td>');
        var $tr = $('<tr>').append($first).append($second);
        return $result.append($tr);
    },
    _renderInnerGroupRow: function ($result, nodes) {
        var $tr = $('<tr>');
        for (var i = 0; i < nodes.length; i++) {
            $tr.append(this._renderInnerField(nodes[i]).contents());
        }
        return $result.append($tr);
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
    _renderStatButton: function (node) {
        var $button = $('<button>').addClass('btn btn-sm oe_stat_button');
        if (node.attrs.icon) {
            $('<div>')
                .addClass('fa fa-fw o_button_icon')
                .addClass(node.attrs.icon)
                .appendTo($button);
        }
        $button.append(_.map(node.children, this._renderNode.bind(this)));
        this._addOnClickAction($button, node);
        this._handleAttributes($button, node);
        return $button;
    },
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
    _renderTabPage: function (page, page_id) {
        var $result = $('<div class="tab-pane" id="' + page_id + '">');
        $result.append(_.map(page.children, this._renderNode.bind(this)));
        return $result;
    },
    _renderTagButton: function (node) {
        var widget = {
            node: node,
            string: (node.attrs.string || '').replace(/_/g, '')
        };
        if (node.attrs.icon) {
            widget.fa_icon = node.attrs.icon.indexOf('fa-') === 0;
        }
        var $button = $(qweb.render('WidgetButton', {widget: widget}));
        this._addOnClickAction($button, node);
        this._handleAttributes($button, node);
        return $button;
    },
    _renderTagField: function (node) {
        return this._renderFieldWidget(node).$el;
    },
    _renderTagForm: function (node) {
        var $result = $('<div/>');
        if (node.attrs.class) {
            $result.addClass(node.attrs.class);
        }
        $result.append(_.map(node.children, this._renderNode.bind(this)));
        return $result;
    },
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

        return $result;
    },
    _renderTagHeader: function (node) {
        var self = this;
        var $statusbar = $('<div>', {class: 'o_form_statusbar'});
        var $buttons = $('<div>', {class: 'o_statusbar_buttons'});
        $statusbar.append($buttons);
        _.each(node.children, function (child) {
            if (child.tag === 'button') {
                $buttons.append(self._renderHeaderButton(child));
            } else if (child.tag === 'field') {
                var widget = self._renderFieldWidget(child);
                $statusbar.append(widget.$el);
            }
        });
        return $statusbar;
    },
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
        return $result;
    },
    _renderTagNotebook: function (node) {
        var self = this;
        var $headers = $('<ul class="nav nav-tabs">');
        var $pages = $('<div class="tab-content nav nav-tabs">');
        _.each(node.children, function (child, index) {
            var pageID = _.uniqueId('notebook_page_');
            var $header = self._renderTabHeader(child, pageID);
            var $page = self._renderTabPage(child, pageID);
            if (index === 0) {
                $header.addClass('active');
                $page.addClass('active');
            }
            self._handleAttributes($header, child, function onEvalCallback (attrs) {
                // if the active tab is invisible, activate the first visible tab instead
                if (attrs.invisible && $header.hasClass('active')) {
                    $header.removeClass('active');
                    $page.removeClass('active');
                    var $firstVisibleTab = $headers.find('li:not(.o_form_invisible):first()');
                    $firstVisibleTab.addClass('active');
                    $pages.find($firstVisibleTab.find('a').attr('href')).addClass('active');
                }
            });
            $headers.append($header);
            $pages.append($page);
        });
        return $('<div class="o_notebook">')
                .data('name', node.attrs.name || '_default_')
                .append($headers)
                .append($pages);
    },
    _renderTagSeparator: function (node) {
        return $('<div/>').addClass('o_horizontal_separator').text(node.attrs.string);
    },
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
     * @override method from BasicRenderer
     * @returns {Deferred}
     */
    _renderView: function () {
        var self = this;
        this.defs = [];
        this.nodeModifiers = [];

        // render the form and evaluate the modifiers
        var $form = this._renderNode(this.arch).addClass(this.className);
        this._evaluateModifiers();

        var defs = this.defs;
        delete this.defs;
        return $.when.apply($, defs).then(function () {
            self.$el.html($form.contents());

            // necessary to allow all sub widgets to use their dimensions in layout
            // related activities, such as autoresize on fieldtexts
            core.bus.trigger('DOM_updated');

            self.$el.toggleClass('o_form_nosheet', !self.has_sheet);
            self.$el.toggleClass('o_form_editable', self.mode === 'edit');
            self.$el.toggleClass('o_form_readonly', self.mode === 'readonly');
            // Attach the tooltips on the fields' label
            _.each(self.widgets, function (widget) {
                if (core.debug || widget.attrs.help || widget.field.help) {
                    var idForLabel = self.idsForLabels[widget.name];
                    var $label = idForLabel ? self.$('label[for=' + idForLabel + ']') : $();
                    self._addFieldTooltip(widget, $label);
                }
            });

        });
    },
});

});
