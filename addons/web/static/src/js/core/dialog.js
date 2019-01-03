odoo.define('web.Dialog', function (require) {
"use strict";

var core = require('web.core');
var dom = require('web.dom');
var Widget = require('web.Widget');

var QWeb = core.qweb;
var _t = core._t;

/**
 * A useful class to handle dialogs.
 * Attributes:
 *
 * ``$footer``
 *   A jQuery element targeting a dom part where buttons can be added. It
 *   always exists during the lifecycle of the dialog.
 **/
var Dialog = Widget.extend({
    tagName: 'main',
    xmlDependencies: ['/web/static/src/xml/dialog.xml'],
    custom_events: _.extend({}, Widget.prototype.custom_events, {
        focus_control_button: '_onFocusControlButton',
    }),
    events: _.extend({} , Widget.prototype.events, {
        'keydown .modal-footer button':'_onFooterButtonKeyDown',
    }),
    /**
     * @param {Widget} parent
     * @param {Object} [options]
     * @param {string} [options.title=Odoo]
     * @param {string} [options.subtitle]
     * @param {string} [options.size=large] - 'large', 'medium' or 'small'
     * @param {boolean} [options.fullscreen=false] - whether or not the dialog
     *        should be open in fullscreen mode (the main usecase is mobile)
     * @param {string} [options.dialogClass] - class to add to the modal-body
     * @param {jQuery} [options.$content]
     *        Element which will be the $el, replace the .modal-body and get the
     *        modal-body class
     * @param {Object[]} [options.buttons]
     *        List of button descriptions. Note: if no buttons, a "ok" primary
     *        button is added to allow closing the dialog
     * @param {string} [options.buttons[].text]
     * @param {string} [options.buttons[].classes]
     *        Default to 'btn-primary' if only one button, 'btn-secondary'
     *        otherwise
     * @param {boolean} [options.buttons[].close=false]
     * @param {function} [options.buttons[].click]
     * @param {boolean} [options.buttons[].disabled]
     * @param {boolean} [options.technical=true]
     *        If set to false, the modal will have the standard frontend style
     *        (use this for non-editor frontend features)
     */
    init: function (parent, options) {
        this._super(parent);
        this._opened = $.Deferred();

        options = _.defaults(options || {}, {
            title: _t('Odoo'), subtitle: '',
            size: 'large',
            fullscreen: false,
            dialogClass: '',
            $content: false,
            buttons: [{text: _t("Ok"), close: true}],
            technical: true,
        });

        this.$content = options.$content;
        this.title = options.title;
        this.subtitle = options.subtitle;
        this.fullscreen = options.fullscreen;
        this.dialogClass = options.dialogClass;
        this.size = options.size;
        this.buttons = options.buttons;
        this.technical = options.technical;
    },
    /**
     * Wait for XML dependencies and instantiate the modal structure (except
     * modal-body).
     *
     * @override
     */
    willStart: function () {
        var self = this;
        return this._super.apply(this, arguments).then(function () {
            // Render modal once xml dependencies are loaded
            self.$modal = $(QWeb.render('Dialog', {
                fullscreen: self.fullscreen,
                title: self.title,
                subtitle: self.subtitle,
                technical: self.technical,
            }));
            switch (self.size) {
                case 'large':
                    self.$modal.find('.modal-dialog').addClass('modal-lg');
                    break;
                case 'small':
                    self.$modal.find('.modal-dialog').addClass('modal-sm');
                    break;
            }
            self.$footer = self.$modal.find(".modal-footer");
            self.set_buttons(self.buttons);
            self.$modal.on('hidden.bs.modal', _.bind(self.destroy, self));
        });
    },
    /**
     * @override
     */
    renderElement: function () {
        this._super();
        // Note: ideally, the $el which is created/set here should use the
        // 'main' tag, we cannot enforce this as it would require to re-create
        // the whole element.
        if (this.$content) {
            this.setElement(this.$content);
        }
        this.$el.addClass('modal-body ' + this.dialogClass);
    },
    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------
    /**
     * @param {Object[]} buttons - @see init
     */
    set_buttons: function (buttons) {
        var self = this;
        this.$footer.empty();
        _.each(buttons, function (buttonData) {
            var $button = dom.renderButton({
                attrs: {
                    class: buttonData.classes || (buttons.length > 1 ? 'btn-secondary' : 'btn-primary'),
                    disabled: buttonData.disabled,
                },
                icon: buttonData.icon,
                text: buttonData.text,
            });
            $button.on('click', function (e) {
                var def;
                if (buttonData.click) {
                    def = buttonData.click.call(self, e);
                }
                if (buttonData.close) {
                    $.when(def).always(self.close.bind(self));
                }
            });
            if (self.technical) {
                self.$footer.append($button);
            } else {
                self.$footer.prepend($button);
            }
        });
    },

    set_title: function (title, subtitle) {
        this.title = title || "";
        if (subtitle !== undefined) {
            this.subtitle = subtitle || "";
        }

        var $title = this.$modal.find('.modal-title').first();
        var $subtitle = $title.find('.o_subtitle').detach();
        $title.html(this.title);
        $subtitle.html(this.subtitle).appendTo($title);

        return this;
    },

    opened: function (handler) {
        return (handler)? this._opened.then(handler) : this._opened;
    },

    /**
     * Show a dialog
     *
     * @param {Object} options
     * @param {boolean} options.shouldFocusButtons  if true, put the focus on
     * the first button primary when the dialog opens
     */
    open: function (options) {
        $('.tooltip').remove(); // remove open tooltip if any to prevent them staying when modal is opened

        var self = this;
        this.appendTo($('<div/>')).then(function () {
            self.$modal.find(".modal-body").replaceWith(self.$el);
            self.$modal.attr('open', true);
            self.$modal.removeAttr("aria-hidden");
            self.$modal.modal('show');
            self._opened.resolve();
            if (options && options.shouldFocusButtons) {
                self._onFocusControlButton();
            }
        });

        return self;
    },

    close: function () {
        this.destroy();
    },

    /**
     * Close and destroy the dialog.
     *
     * @param {Object} [options]
     * @param {Object} [options.infos] if provided and `silent` is unset, the
     *   `on_close` handler will pass this information related to closing this
     *   information.
     * @param {boolean} [options.silent=false] if set, do not call the
     *   `on_close` handler.
     */
    destroy: function (options) {
        // Need to trigger before real destroy but if 'closed' handler destroys
        // the widget again, we want to avoid infinite recursion
        if (!this.__closed) {
            this.__closed = true;
            this.trigger('closed', options);
        }

        if (this.isDestroyed()) {
            return;
        }
        var isFocusSet = this._focusOnClose();

        this._super();

        $('.tooltip').remove(); //remove open tooltip if any to prevent them staying when modal has disappeared
        if (this.$modal) {
            this.$modal.modal('hide');
            this.$modal.remove();
        }

        if (!isFocusSet) {
            var modals = $('body > .modal').filter(':visible');
            if (modals.length) {
                modals.last().focus();
                // Keep class modal-open (deleted by bootstrap hide fnct) on body to allow scrolling inside the modal
                $('body').addClass('modal-open');
            }
        }
    },
    /**
     * adds the keydown behavior to the dialogs after external files modifies
     * its DOM.
     */
    rebindButtonBehavior: function () {
        this.$footer.on('keydown', this._onFooterButtonKeyDown);
    },
    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------
    /**
     * Manages the focus when the dialog closes. The default behavior is to set the focus on the top-most opened popup.
     * The goal of this function is to be overridden by all children of the dialog class.
     *
     * @returns: boolean  should return true if the focus has already been set else false.
     */
    _focusOnClose: function() {
        return false;
    },
    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------
    /**
     * Moves the focus to the first button primary in the footer of the dialog
     *
     * @private
     * @param {odooEvent} e
     */
    _onFocusControlButton: function (e) {
        if (this.$footer) {
            if (e) {
                e.stopPropagation();
            }
            this.$footer.find('.btn-primary:visible:first()').focus();
        }
    },
    /**
     * Manages the TAB key on the buttons. If you the focus is on a primary
     * button and the users tries to tab to go to the next button, display
     * a tooltip
     *
     * @param {jQueryEvent} e
     * @private
     */
    _onFooterButtonKeyDown: function (e) {
        switch(e.which) {
            case $.ui.keyCode.TAB:
                if (!e.shiftKey && e.target.classList.contains("btn-primary")) {
                    e.preventDefault();
                    var $primaryButton = $(e.target);
                    $primaryButton.tooltip({
                        delay: {show: 200, hide:0},
                        title: function(){
                            return QWeb.render('FormButton.tooltip',{title:$primaryButton.text().toUpperCase()});
                        },
                        trigger: 'manual',
                    });
                    $primaryButton.tooltip('show');
                }
                break;
        }
    }
});

// static method to open simple alert dialog
Dialog.alert = function (owner, message, options) {
    var buttons = [{
        text: _t("Ok"),
        close: true,
        click: options && options.confirm_callback,
    }];
    return new Dialog(owner, _.extend({
        size: 'medium',
        buttons: buttons,
        $content: $('<main/>', {
            role: 'alert',
            text: message,
        }),
        title: _t("Alert"),
    }, options)).open({shouldFocusButtons:true});
};

// static method to open simple confirm dialog
Dialog.confirm = function (owner, message, options) {
    var buttons = [
        {
            text: _t("Ok"),
            classes: 'btn-primary',
            close: true,
            click: options && options.confirm_callback,
        },
        {
            text: _t("Cancel"),
            close: true,
            click: options && options.cancel_callback
        }
    ];
    return new Dialog(owner, _.extend({
        size: 'medium',
        buttons: buttons,
        $content: $('<main/>', {
            role: 'alert',
            text: message,
        }),
        title: _t("Confirmation"),
    }, options)).open({shouldFocusButtons:true});
};

/**
 * Static method to open double confirmation dialog.
 *
 * @param {Widget} owner
 * @param {string} message
 * @param {Object} [options] @see Dialog.init @see Dialog.confirm
 * @param {string} [options.securityLevel="warning"] - bootstrap color
 * @param {string} [options.securityMessage="I am sure about this"]
 * @returns {Dialog} (open() is automatically called)
 */
Dialog.safeConfirm = function (owner, message, options) {
    var $checkbox = dom.renderCheckbox({
        text: options && options.securityMessage || _t("I am sure about this."),
    }).addClass('mb0');
    var $securityCheck = $('<div/>', {
        class: 'alert alert-' + (options && options.securityLevel || 'warning') + ' mt8 mb0',
    }).prepend($checkbox);
    var $content;
    if (options && options.$content) {
        $content = options.$content;
        delete options.$content;
    } else {
        $content = $('<div>', {
            text: message,
        });
    }
    $content = $('<main/>', {role: 'alert'}).append($content, $securityCheck);

    var buttons = [
        {
            text: _t("Ok"),
            classes: 'btn-primary o_safe_confirm_button',
            close: true,
            click: options && options.confirm_callback,
            disabled: true,
        },
        {
            text: _t("Cancel"),
            close: true,
            click: options && options.cancel_callback
        }
    ];
    var dialog = new Dialog(owner, _.extend({
        size: 'medium',
        buttons: buttons,
        $content: $content,
        title: _t("Confirmation"),
    }, options));
    dialog.opened(function () {
        var $button = dialog.$footer.find('.o_safe_confirm_button');
        $securityCheck.on('click', 'input[type="checkbox"]', function (ev) {
            $button.prop('disabled', !$(ev.currentTarget).prop('checked'));
        });
    });
    return dialog.open();
};

return Dialog;

});
