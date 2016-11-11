odoo.define('web.Dialog', function (require) {
"use strict";

var core = require('web.core');
var Widget = require('web.Widget');

var QWeb = core.qweb;
var _t = core._t;

/**
    A useful class to handle dialogs.

    Attributes:
    - $footer: A jQuery element targeting a dom part where buttons can be added. It always exists
    during the lifecycle of the dialog.
*/
var Dialog = Widget.extend({
    /**
        Constructor.

        @param {Widget} parent
        @param {dictionary} options
            - title
            - subtitle
            - size: one of the following: 'large', 'medium', 'small'
            - dialogClass: class to add to the modal-body
            - buttons: It must be a list of dictionaries -> text, classes, close, click, disabled
                -> If no buttons, a "ok" primary button is added with close = true
                -> By default: close = false and classes = 'btn-primary' if only one button and 'btn-default' if many buttons
            - $content: Some content to replace this.$el .
    */
    init: function (parent, options) {
        this._super(parent);
        this._opened = $.Deferred();

        options = _.defaults(options || {}, {
            title: _t('Odoo'), subtitle: '',
            size: 'large',
            dialogClass: '',
            $content: false,
            buttons: [{text: _t("Ok"), close: true}]
        });

        this.$content = options.$content;

        this.title = options.title;
        this.subtitle = options.subtitle;
        this.$modal = $(QWeb.render('Dialog', {title: this.title, subtitle: this.subtitle}));

        switch(options.size) {
            case 'large':
                this.$modal.find('.modal-dialog').addClass('modal-lg');
                break;
            case 'small':
                this.$modal.find('.modal-dialog').addClass('modal-sm');
                break;
        }

        this.dialogClass = options.dialogClass;
        this.$footer = this.$modal.find(".modal-footer");

        this.set_buttons(options.buttons);

        this.$modal.on('hidden.bs.modal', _.bind(this.destroy, this));
    },

    renderElement: function() {
        this._super();
        if(this.$content) {
            this.setElement(this.$content);
        }
        this.$el.addClass('modal-body ' + this.dialogClass);
    },

    set_buttons: function(buttons) {
        var self = this;

        self.$footer.empty();

        _.each(buttons, function(b) {
            var text = b.text || "";
            var classes = b.classes || ((buttons.length === 1)? "btn-primary" : "btn-default");

            var $b = $(QWeb.render('WidgetButton', { widget : { string: text, node: { attrs: {'class': classes} }}}));
            $b.prop('disabled', b.disabled);
            $b.on('click', function(e) {
                var click_def;
                if(b.click) {
                    click_def = b.click.call(self, e);
                }
                if(b.close) {
                    $.when(click_def).always(self.close.bind(self));
                }
            });
            self.$footer.append($b);
        });
    },

    set_title: function(title, subtitle) {
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

    opened: function(handler) {
        return (handler)? this._opened.then(handler) : this._opened;
    },

    open: function() {
        $('.tooltip').remove(); // remove open tooltip if any to prevent them staying when modal is opened

        var self = this;
        this.replace(this.$modal.find(".modal-body")).then(function() {
            self.$modal.modal('show');
            self._opened.resolve();
        });

        return self;
    },

    close: function() {
        this.$modal.modal('hide');
    },

    destroy: function(reason) {
        if (this.isDestroyed()) {
            return;
        }

        this.trigger("closed", reason);

        this._super();

        $('.tooltip').remove(); //remove open tooltip if any to prevent them staying when modal has disappeared
        this.$modal.modal('hide');
        this.$modal.remove();

        setTimeout(function () { // Keep class modal-open (deleted by bootstrap hide fnct) on body to allow scrolling inside the modal
            var modals = $('body > .modal').filter(':visible');
            if(modals.length) {
                modals.last().focus();
                $('body').addClass('modal-open');
            }
        }, 0);
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
            click: options && options.confirm_callback
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

return Dialog;

});
