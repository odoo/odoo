odoo.define('partner.autocomplete.fieldchar', function (require) {
'use strict';

var basic_fields = require('web.basic_fields');
var core = require('web.core');
var field_registry = require('web.field_registry');
var AutocompleteMixin = require('partner.autocomplete.Mixin');

var QWeb = core.qweb;

var FieldChar = basic_fields.FieldChar;

/**
 * FieldChar extension to suggest existing companies when changing the company
 * name on a res.partner view (indeed, it is designed to change the "name",
 * "website" and "image" fields of records of this model).
 */
var FieldAutocomplete = FieldChar.extend(AutocompleteMixin, {
    description: "",
    className: 'o_field_partner_autocomplete',
    debounceSuggestions: 400,
    resetOnAnyFieldChange: true,

    jsLibs: [
        '/partner_autocomplete/static/lib/jsvat.js'
    ],

    events: _.extend({}, FieldChar.prototype.events, {
        'keyup': '_onKeyup',
        'mousedown .o_partner_autocomplete_suggestion': '_onMousedown',
        'focusout': '_onFocusout',
        'mouseenter .o_partner_autocomplete_suggestion': '_onHoverDropdown',
        'click .o_partner_autocomplete_suggestion': '_onSuggestionClicked',
    }),

    /**
     * @constructor
     * Prepares the basic rendering of edit mode by setting the root to be a
     * div.dropdown.open.
     * @see FieldChar.init
     */
    init: function () {
        this._super.apply(this, arguments);

        // If the autocomplete is applied to vat field, only search valid vat number
        this.onlyVAT = this.name === 'vat';

        if (this.mode === 'edit') {
            this.tagName = 'div';
            this.className += ' dropdown open';
        }

        if (this.debounceSuggestions > 0) {
            this._suggestCompanies = _.debounce(this._suggestCompanies.bind(this), this.debounceSuggestions);
        }
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Check if the autocomplete should be active
     * Active :
     *  - only when creating new record
     *  - on model res.partner and is_company=true
     *  - on model res.company
     *
     * @returns {boolean}
     * @private
     */
    _isActive: function () {
        return this.model === 'res.company' ||
            (
                this.model === 'res.partner'
                && this.record.data.is_company
                && !(this.record.data && this.record.data.id)
            );
    },

    /**
     *
     * @private
     */
    _removeDropdown: function () {
        if (this.$dropdown) {
            this.$dropdown.remove();
            this.$dropdown = undefined;
        }
    },

    /**
     * Adds the <input/> element and prepares it. Note: the dropdown rendering
     * is handled outside of the rendering routine (but instead by reacting to
     * user input).
     *
     * @override
     * @private
     */
    _renderEdit: function () {
        this.$el.empty();
        // Prepare and add the input
        this._prepareInput().appendTo(this.$el);
    },

    /**
     * Selects the given company suggestions by notifying changes to the view
     * for the "name", "website" and "image" fields. This is of course intended
     * to work only with the "res.partner" form view.
     *
     * @private
     * @param {Object} company
     */
    _selectCompany: function (company) {
        var self = this;
        this._getCreateData(company).then(function (data) {
            if (data.logo) {
                var logoField = self.model === 'res.partner' ? 'image' : 'logo';
                data.company[logoField] = data.logo;
            }

            // Some fields are unnecessary in res.company
            if (self.model === 'res.company') {
                var fields = 'comment,child_ids,bank_ids,additional_info'.split(',');
                fields.forEach(function (field) {
                    delete data.company[field];
                });
            }

            self._setOne2ManyField('child_ids', data.company.child_ids);
            delete data.company.child_ids;

            self._setOne2ManyField('bank_ids', data.company.bank_ids);
            delete data.company.bank_ids;

            self.trigger_up('field_changed', {
                dataPointID: self.dataPointID,
                changes: data.company,
                onSuccess: function () {
                    // update the input's value directly
                    if (self.onlyVAT)
                        self.$input.val(self._formatValue(company.vat));
                    else
                        self.$input.val(self._formatValue(company.name));
                },
            });
        });
        this._removeDropdown();
    },

    _setOne2ManyField: function (field, list) {
        var self = this;
        var viewType = this.record.viewType;
        if (list && this.record.fieldsInfo[viewType] && this.record.fieldsInfo[viewType][field]) {
            list.forEach(function (item) {
                var changes = {};
                changes[field] = {
                    operation: 'CREATE',
                    data: item,
                };

                self.trigger_up('field_changed', {
                    dataPointID: self.dataPointID,
                    changes: changes,
                });
            });
        }
    },

    /**
     * Shows the dropdown with the suggestions. If one is
     * already opened, it removes the old one before rerendering the dropdown.
     *
     * @private
     */
    _showDropdown: function () {
        this._removeDropdown();
        if (this.suggestions.length > 0) {
            this.$dropdown = $(QWeb.render('partner_autocomplete.dropdown', {
                suggestions: this.suggestions,
            }));
            this.$dropdown.appendTo(this.$el);
        }
    },

    /**
     * Shows suggestions according to the given value.
     * Note: this method is debounced (@see init).
     *
     * @private
     * @param {string} value - searched term
     */
    _suggestCompanies: function (value) {
        var self = this;
        if (this._validateSearchTerm(value, this.onlyVAT) && this._isOnline()) {
            return this._autocomplete(value).then(function (suggestions) {
                if (suggestions && suggestions.length) {
                    self.suggestions = suggestions;
                    self._showDropdown();
                } else {
                    self._removeDropdown();
                }
            });
        } else {
            this._removeDropdown();
        }
    },


    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Called on focusout -> removes the suggestions dropdown.
     *
     * @private
     */
    _onFocusout: function () {
        this._removeDropdown();
    },

    /**
     * Called when hovering a suggestion in the dropdown -> sets it as active.
     *
     * @private
     * @param {Event} e
     */
    _onHoverDropdown: function (e) {
        this.$dropdown.find('.active').removeClass('active');
        $(e.currentTarget).parent().addClass('active');
    },

    /**
     * @override of FieldChar (called when the user is typing text)
     * Checks the <input/> value and shows suggestions according to
     * this value.
     *
     * @private
     */
    _onInput: function () {
        this._super.apply(this, arguments);
        if (this._isActive()) {
            this._suggestCompanies(this.$input.val());
        }
    },

    /**
     * @override of FieldChar
     * Changes the "up" and "down" key behavior when the dropdown is opened (to
     * navigate through dropdown suggestions).
     * Triggered by keydown to execute the navigation multiple times when the
     * user keeps the "down" or "up" pressed.
     *
     * @private
     * @param {Event} e
     */
    _onKeydown: function (e) {
        switch (e.which) {
            case $.ui.keyCode.UP:
            case $.ui.keyCode.DOWN:
                if (!this.$dropdown) {
                    break;
                }
                e.preventDefault();
                var $suggestions = this.$dropdown.children();
                var $active = $suggestions.filter('.active');
                var $to;
                if ($active.length) {
                    $to = e.which === $.ui.keyCode.DOWN ?
                        $active.next() :
                        $active.prev();
                } else {
                    $to = $suggestions.first();
                }
                if ($to.length) {
                    $active.removeClass('active');
                    $to.addClass('active');
                }
                return;
        }
        this._super.apply(this, arguments);
    },

    /**
     * Called on keyup events to:
     * -> remove the suggestions dropdown when hitting the "escape" key
     * -> select the highlighted suggestion when hitting the "enter" key
     *
     * @private
     * @param {Event} e
     */
    _onKeyup: function (e) {
        switch (e.which) {
            case $.ui.keyCode.ESCAPE:
                e.preventDefault();
                this._removeDropdown();
                break;
            case $.ui.keyCode.ENTER:
                if (!this.$dropdown) {
                    break;
                }
                e.preventDefault();
                var $active = this.$dropdown.find('.o_partner_autocomplete_suggestion.active');
                if (!$active.length) {
                    return;
                }
                this._selectCompany(this.suggestions[$active.data('index')]);
                break;
        }
    },

    /**
     * Called on mousedown event on a suggestion -> prevent default
     * action so that the <input/> element does not lose the focus.
     *
     * @private
     * @param {Event} e
     */
    _onMousedown: function (e) {
        e.preventDefault(); // prevent losing focus on suggestion click
    },

    /**
     * Called when a dropdown suggestion is clicked -> trigger_up changes for
     * some fields in the view (not only this <input/> one) with the associated
     * data (@see _selectCompany).
     *
     * @private
     * @param {Event} e
     */
    _onSuggestionClicked: function (e) {
        e.preventDefault();
        this._selectCompany(this.suggestions[$(e.currentTarget).data('index')]);
    },
});

field_registry.add('field_partner_autocomplete', FieldAutocomplete);

return FieldAutocomplete;
});
