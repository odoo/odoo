odoo.define('web.Dialog', function (require) {
"use strict";

var core = require('web.core');
var dom = require('web.dom');
var Widget = require('web.Widget');
const OwlDialog = require('web.OwlDialog');

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
    xmlDependencies: ['/web/static/src/legacy/xml/dialog.xml'],
    custom_events: _.extend({}, Widget.prototype.custom_events, {
        focus_control_button: '_onFocusControlButton',
        close_dialog: '_onCloseDialog',
    }),
    events: _.extend({}, Widget.prototype.events, {
        'keydown .modal-footer button': '_onFooterButtonKeyDown',
    }),
    /**
     * @param {Widget} parent
     * @param {Object} [options]
     * @param {string} [options.title=Odoo]
     * @param {string} [options.subtitle]
     * @param {string} [options.size=large] - 'extra-large', 'large', 'medium'
     *        or 'small'
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
     * @param {jQueryElement} [options.$parentNode]
     *        Element in which dialog will be appended, by default it will be
     *        in the body
     * @param {boolean|string} [options.backdrop='static']
     *        The kind of modal backdrop to use (see BS documentation)
     * @param {boolean} [options.renderHeader=true]
     *        Whether or not the dialog should be rendered with header
     * @param {boolean} [options.renderFooter=true]
     *        Whether or not the dialog should be rendered with footer
     * @param {function} [options.onForceClose]
     *        Callback that triggers when the modal is closed by other means than with the buttons
     *        e.g. pressing ESC
     */
    init: function (parent, options) {
        var self = this;
        this._super(parent);
        this._opened = new Promise(function (resolve) {
            self._openedResolver = resolve;
        });
        if (this.on_attach_callback) {
            this._opened = this.opened(this.on_attach_callback);
        }
        options = _.defaults(options || {}, {
            title: _t('Odoo'), subtitle: '',
            size: 'large',
            fullscreen: false,
            dialogClass: '',
            $content: false,
            buttons: [{text: _t("Ok"), close: true}],
            technical: true,
            $parentNode: false || $(document.body.querySelector(".o_dialog_container")),
            backdrop: 'static',
            renderHeader: true,
            renderFooter: true,
            onForceClose: false,
        });

        this.$content = options.$content;
        this.title = options.title;
        this.subtitle = options.subtitle;
        this.fullscreen = options.fullscreen;
        this.dialogClass = options.dialogClass;
        this.size = options.size;
        this.buttons = options.buttons;
        this.technical = options.technical;
        this.$parentNode = options.$parentNode;
        this.backdrop = options.backdrop;
        this.renderHeader = options.renderHeader;
        this.renderFooter = options.renderFooter;
        this.onForceClose = options.onForceClose;

        core.bus.on('close_dialogs', this, this.destroy.bind(this));
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
                renderHeader: self.renderHeader,
                renderFooter: self.renderFooter,
            }));
            switch (self.size) {
                case 'extra-large':
                    self.$modal.find('.modal-dialog').addClass('modal-xl');
                    break;
                case 'large':
                    self.$modal.find('.modal-dialog').addClass('modal-lg');
                    break;
                case 'small':
                    self.$modal.find('.modal-dialog').addClass('modal-sm');
                    break;
            }
            if (self.renderFooter) {
                self.$footer = self.$modal.find(".modal-footer");
                self.set_buttons(self.buttons);
            }
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
        this._setButtonsTo(this.$footer, buttons);
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
            if (self.isDestroyed()) {
                return;
            }
            self.$modal.find(".modal-body").replaceWith(self.$el);
            self.$modal.attr('open', true);
            self.$modal.removeAttr("aria-hidden");
            if (self.$parentNode) {
                self.$modal.appendTo(self.$parentNode);
            }
            self.$modal.modal({
                show: true,
                backdrop: self.backdrop,
                keyboard: false,
            });
            self._openedResolver();
            if (options && options.shouldFocusButtons) {
                self._onFocusControlButton();
            }

            // Notifies OwlDialog to adjust focus/active properties on owl dialogs
            OwlDialog.display(self);

            // Notifies new webclient to adjust UI active element
            core.bus.trigger("legacy_dialog_opened", self);
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

        // Notifies OwlDialog to adjust focus/active properties on owl dialogs.
        // Only has to be done if the dialog has been opened (has an el).
        if (this.el) {
            OwlDialog.hide(this);

            // Notifies new webclient to adjust UI active element
            core.bus.trigger("legacy_dialog_destroyed", this);
        }

        // Triggers the onForceClose event if the callback is defined
        if (this.onForceClose) {
            this.onForceClose();
        }
        var isFocusSet = this._focusOnClose();

        this._super();

        $('.tooltip').remove(); //remove open tooltip if any to prevent them staying when modal has disappeared
        if (this.$modal) {
            if (this.on_detach_callback) {
                this.on_detach_callback();
            }
            this.$modal.modal('hide');
            this.$modal.remove();
        }

        const modals = $('.modal[role="dialog"]').filter(':visible').filter(this._isBlocking);
        if (modals.length) {
            if (!isFocusSet) {
                modals.last().focus();
            }
            // Keep class modal-open (deleted by bootstrap hide fnct) on body to allow scrolling inside the modal
            $('body').addClass('modal-open');
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
    /**
     * Render and set the given buttons into a target element
     *
     * @private
     * @param {jQueryElement} $target The destination of the rendered buttons
     * @param {Array} buttons The array of buttons to render
     */
    _setButtonsTo($target, buttons) {
        var self = this;
        $target.empty();
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
                    self.onForceClose = false;
                    Promise.resolve(def).then(self.close.bind(self));
                }
            });
            if (self.technical) {
                $target.append($button);
            } else {
                $target.prepend($button);
            }
        });
    },
    /**
     * Returns false for non-"blocking" dialogs.
     * This is intended to be overridden by subclasses.
     *
     * @private
     * @param {int} index
     * @param {element} el The element of a dialog.
     * @returns {boolean}
     */
    _isBlocking(index, el) {
        return true;
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------
    /**
     * @private
     */
    _onCloseDialog: function (ev) {
        ev.stopPropagation();
        this.close();
    },
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
        onForceClose: options && (options.onForceClose || options.confirm_callback),
    }, options)).open({shouldFocusButtons:true});
};

// static method to open simple confirm dialog
Dialog.confirm = function (owner, message, options) {
    let clickProm;
    var buttons = [
        {
            text: _t("Ok"),
            classes: 'btn-primary',
            close: true,
            click: options && options.confirm_callback && (() => {
                clickProm = clickProm || options.confirm_callback() || Promise.resolve();
                return clickProm;
            }),
        },
        {
            text: _t("Cancel"),
            close: true,
            click: options && options.cancel_callback && (() => {
                clickProm = clickProm || options.cancel_callback() || Promise.resolve();
                return clickProm;
            }),
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
        onForceClose: options && (options.onForceClose || options.cancel_callback),
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
        onForceClose: options && (options.onForceClose || options.cancel_callback),
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
