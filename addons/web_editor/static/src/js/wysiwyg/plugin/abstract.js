odoo.define('web_editor.wysiwyg.plugin.abstract', function (require) {
'use strict';

var Class = require('web.Class');
var mixins = require('web.mixins');
var ServicesMixin = require('web.ServicesMixin');
var wysiwygTranslation = require('web_editor.wysiwyg.translation');
var wysiwygOptions = require('web_editor.wysiwyg.options');

//--------------------------------------------------------------------------
// AbstractPlugin for summernote module API
//--------------------------------------------------------------------------

var AbstractPlugin = Class.extend(mixins.EventDispatcherMixin, ServicesMixin).extend({
    /**
     * Use this prop if you want to extend a summernote plugin.
     */
    init: function (context) {
        var self = this;
        this._super.apply(this, arguments);
        this.setParent(context.options.parent);
        this.context = context;

        if (!this.context.invoke) {
            // for use outside of wysiwyg/summernote
            this.context.invoke = function () {};
        }

        this.$editable = context.layoutInfo.editable;
        this.editable = this.$editable[0];
        this.document = this.editable.ownerDocument;
        this.window = this.document.defaultView;
        this.summernote = this.window._summernoteSlave || $.summernote; // if the target is in iframe
        this.ui = this.summernote.ui;
        this.$editingArea = context.layoutInfo.editingArea;
        this.options = _.defaults(context.options || {}, wysiwygOptions);
        this.lang = wysiwygTranslation;
        this._addButtons();
        if (this.events) {
            this.events = _.clone(this.events);
            _.each(_.keys(this.events), function (key) {
                var value = self.events[key];
                if (typeof value === 'string') {
                    value = self[value].bind(self);
                }
                if (key.indexOf('summernote.') === 0) {
                    self.events[key] = value;
                } else {
                    delete self.events[key];
                    key = key.split(' ');
                    if (key.length > 1) {
                        self.context.layoutInfo.editor.on(key[0], key.slice(1).join(' '), value);
                    } else {
                        self.context.layoutInfo.editor.on(key, value);
                    }
                }
            });
        }
    },

    //--------------------------------------------------------------------------
    // Public summernote module API
    //--------------------------------------------------------------------------

    shouldInitialize: function () {
        return true;
    },
    initialize: function () {},

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Override to add buttons.
     */
    _addButtons: function () {},
    /**
     * Creates a dropdown button with its contents and behavior.
     *
     * @param {str} optionName
     * @param {str} buttonIcon (ex.: 'note-icon-align')
     * @param {str} buttonTooltip (ex.: 'Align Paragraph')
     * @param {Object[]} values (ex.: [{value: 'padding-small', string: 'S'}])
     * @param {function} onclick
     */
    _createDropdownButton: function (optionName, buttonIcon, buttonTooltip, values, onclick) {
        var self = this;

        if (!onclick) {
            onclick = function (e) {
                var classNames = _.map(values, function (item) {
                    return item.value;
                }).join(' ');
                var $target = $(self.context.invoke('editor.restoreTarget'));
                $target.removeClass(classNames);
                if ($(e.target).data('value')) {
                    $target.addClass($(e.target).data('value'));
                }
            };
        }
        if (optionName) {
            this.context.memo('button.' + optionName, function () {
                return self._renderDropdownButton(buttonIcon, buttonTooltip, values, onclick);
            });
        } else {
            return this._renderDropdownButton(buttonIcon, buttonTooltip, values, onclick);
        }
    },
    /**
     * Creates a button to toggle a class.
     *
     * @param {str} optionName
     * @param {str} buttonIcon (ex.: 'note-icon-align')
     * @param {str} buttonTooltip (ex.: 'Align Paragraph')
     * @param {str} className
     */
    _createToggleButton: function (optionName, buttonIcon, buttonTooltip, className) {
        var self = this;
        return this._createButton(optionName, buttonIcon, buttonTooltip, function () {
            var $target = $(self.context.invoke('editor.restoreTarget'));
            $target.toggleClass(className);
        });
    },
    /**
     * Creates a button.
     *
     * @param {str} optionName
     * @param {str} buttonIcon (ex.: 'note-icon-align')
     * @param {str} buttonTooltip (ex.: 'Align Paragraph')
     * @param {function} onclick
     */
    _createButton: function (optionName, buttonIcon, buttonTooltip, onclick) {
        var self = this;
        if (optionName) {
            this.context.memo('button.' + optionName, function () {
                return self._renderButton(buttonIcon, buttonTooltip, onclick);
            });
        } else {
            return this._renderButton(buttonIcon, buttonTooltip, onclick);
        }
    },
    /**
     * Helper function to _createButton: renders the button.
     *
     * @param {str} buttonIcon (ex.: 'note-icon-align')
     * @param {str} buttonTooltip (ex.: 'Align Paragraph')
     * @param {function} onclick
     * @returns {JQuery}
     */
    _renderButton: function (buttonIcon, buttonTooltip, onclick) {
        var self = this;
        return this.context.invoke('buttons.button', {
            contents: buttonIcon.indexOf('<') === -1 ? this.ui.icon(buttonIcon) : buttonIcon,
            tooltip: buttonTooltip,
            click: function (e) {
                e.preventDefault();
                self.context.invoke('editor.beforeCommand');
                onclick(e);
                self.editable.normalize();
                self.context.invoke('editor.saveRange');
                self.context.invoke('editor.afterCommand');
            },
        }).render();
    },
    /**
     * Helper function to _createDropdownButton: renders the dropdown button.
     *
     * @param {str} buttonIcon (ex.: 'note-icon-align')
     * @param {str} buttonTooltip (ex.: 'Align Paragraph')
     * @param {Object[]} values (ex.: [{value: 'padding-small', string: 'S'}])
     * @param {function} onclick
     * @param {JQuery}
     */
    _renderDropdownButton: function (buttonIcon, buttonTooltip, values, onclick) {
        return this.ui.buttonGroup([
            this.context.invoke('buttons.button', {
                className: 'dropdown-toggle',
                contents: buttonIcon.indexOf('<') === -1 ?
                    this.ui.dropdownButtonContents(this.ui.icon(buttonIcon), this.options) : buttonIcon,
                tooltip: buttonTooltip,
                data: {
                    toggle: 'dropdown'
                }
            }),
            this.ui.dropdown({
                items: values,
                template: function (item) {
                    return item.string;
                },
                click: this._wrapCommand(function (e) {
                    e.preventDefault();
                    onclick(e);
                }),
            })
        ]).render();
    },
    /**
     * Wraps a given function between common actions required
     * for history (undo/redo) and the maintenance of the DOM/range.
     *
     * @param {function} fn
     * @returns {any} the return of fn
     */
    _wrapCommand: function (fn) {
        var self = this;
        return function () {
            self.context.invoke('editor.restoreRange');
            self.context.invoke('editor.beforeCommand');
            var res = fn.apply(self, arguments);
            self.editable.normalize();
            self.context.invoke('editor.saveRange');
            self.context.invoke('editor.afterCommand');
            return res;
        };
    },

});

return AbstractPlugin;

});
