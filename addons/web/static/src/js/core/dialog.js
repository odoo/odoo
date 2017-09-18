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
    xmlDependencies: ['/web/static/src/xml/dialog.xml'],

    /**
     * @param {Widget} parent
     * @param {Object} [options]
     * @param {string} [options.title=Odoo]
     * @param {string} [options.subtitle]
     * @param {string} [options.size=large] - 'large', 'medium' or 'small'
     * @param {string} [options.dialogClass] - class to add to the modal-body
     * @param {jQuery} [options.$content]
     *        Element which will be the $el, replace the .modal-body and get the
     *        modal-body class
     * @param {Object[]} [options.buttons]
     *        List of button descriptions. Note: if no buttons, a "ok" primary
     *        button is added to allow closing the dialog
     * @param {string} [options.buttons[].text]
     * @param {string} [options.buttons[].classes]
     *        Default to 'btn-primary' if only one button, 'btn-default'
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
            dialogClass: '',
            $content: false,
            buttons: [{text: _t("Ok"), close: true}],
            technical: true,
        });

        this.$content = options.$content;
        this.title = options.title;
        this.subtitle = options.subtitle;
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
        if (this.$content) {
            this.setElement(this.$content);
        }
        this.$el.addClass('modal-body ' + this.dialogClass);
    },
    /**
     * @param {Object[]} buttons - @see init
     */
    set_buttons: function (buttons) {
        var self = this;
        this.$footer.empty();
        _.each(buttons, function (buttonData) {
            var $button = dom.renderButton({
                attrs: {
                    class: buttonData.classes || (buttons.length > 1 ? 'btn-default' : 'btn-primary'),
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
            self.$footer.append($button);
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

    open: function () {
        $('.tooltip').remove(); // remove open tooltip if any to prevent them staying when modal is opened

        var self = this;
        this.appendTo($('<div/>')).then(function () {
            self.$modal.find(".modal-body").replaceWith(self.$el);
            self.$modal.modal('show');
            self._opened.resolve();
        });

        return self;
    },

    close: function () {
        this.destroy();
    },

    destroy: function (reason) {
        // Need to trigger before real destroy but if 'closed' handler destroys
        // the widget again, we want to avoid infinite recursion
        if (!this.__closed) {
            this.__closed = true;
            this.trigger("closed", reason);
        }

        if (this.isDestroyed()) {
            return;
        }
        this._super();

        $('.tooltip').remove(); //remove open tooltip if any to prevent them staying when modal has disappeared
        if (this.$modal) {
            this.$modal.modal('hide');
            this.$modal.remove();
        }

        var modals = $('body > .modal').filter(':visible');
        if (modals.length) {
            modals.last().focus();
            // Keep class modal-open (deleted by bootstrap hide fnct) on body to allow scrolling inside the modal
            $('body').addClass('modal-open');
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
        $content: $('<div>', {
            text: message,
        }),
        title: _t("Alert"),
    }, options)).open();
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
        $content: $('<div>', {
            text: message,
        }),
        title: _t("Confirmation"),
    }, options)).open();
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
    $content = $('<div/>').append($content, $securityCheck);

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
