odoo.define('web.Dialog', ['web.core', 'web.Widget'], function (require) {
"use strict";

var core = require('web.core');
var Widget = require('web.Widget');

var QWeb = core.qweb;
var opened_modals = [];

/**
    A useful class to handle dialogs.

    Attributes:
    - $buttons: A jQuery element targeting a dom part where buttons can be added. It always exists
    during the lifecycle of the dialog.
*/
var Dialog = Widget.extend({
    dialog_title: "",
    /**
        Constructor.

        @param {Widget} parent
        @param {dictionary} options A dictionary that will be forwarded to jQueryUI Dialog. Additionaly, that
            dictionary can contain the following keys:
            - size: one of the following: 'large', 'medium', 'small'
            - dialogClass: class to add to the body of dialog
            - buttons: Deprecated. The buttons key is not propagated to jQueryUI Dialog. It must be a dictionary (key = button
                label, value = click handler) or a list of dictionaries (each element in the dictionary is send to the
                corresponding method of a jQuery element targeting the <button> tag). It is deprecated because all dialogs
                in OpenERP must be personalized in some way (button in red, link instead of button, ...) and this
                feature does not allow that kind of personalization.
            - destroy_on_close: Default true. If true and the dialog is closed, it is automatically destroyed.
        @param {jQuery object} content Some content to replace this.$el .
    */
    init: function (parent, options, content) {
        this._super(parent);
        this.content_to_set = content;
        this.dialog_options = {
            destroy_on_close: true,
            size: 'large', //'medium', 'small'
            buttons: null,
        };
        if (options) {
            _.extend(this.dialog_options, options);
        }
        this.on("closing", this, this._closing);
        this.$buttons = $('<div class="modal-footer"><span class="oe_dialog_custom_buttons"/></div>');
    },
    renderElement: function() {
        if (this.content_to_set) {
            this.setElement(this.content_to_set);
        } else if (this.template) {
            this._super();
        }
    },
    /**
        Opens the popup. Inits the dialog if it is not already inited.

        @return this
    */
    open: function() {
        if (!this.dialog_inited) {
            this.init_dialog();
        }
        this.$buttons.insertAfter(this.$dialog_box.find(".modal-body"));
        $('.tooltip').remove(); //remove open tooltip if any to prevent them staying when modal is opened
        //add to list of currently opened modal
        opened_modals.push(this.$dialog_box);
        return this;
    },
    _add_buttons: function(buttons) {
        var self = this;
        var $customButons = this.$buttons.find('.oe_dialog_custom_buttons').empty();
        _.each(buttons, function(fn, text) {
            // buttons can be object or array
            var pre_text  = fn.pre_text || "";
            var post_text = fn.post_text || "";
            var oe_link_class = fn.oe_link_class;
            if (!_.isFunction(fn)) {
                text = fn.text;
                fn = fn.click;
            }
            var $but = $(QWeb.render('WidgetButton', { widget : { pre_text: pre_text, post_text: post_text, string: text, node: { attrs: {'class': oe_link_class} }}}));
            $customButons.append($but);
            $but.filter('button').on('click', function(ev) {
                fn.call(self.$el, ev);
            });
        });
    },
    /**
        Initializes the popup.

        @return The result returned by start().
    */
    init_dialog: function() {
        var self = this;
        var options = _.extend({}, this.dialog_options);
        options.title = options.title || this.dialog_title;
        if (options.buttons) {
            this._add_buttons(options.buttons);
            delete(options.buttons);
        }
        this.renderElement();
        this.$dialog_box = $(QWeb.render('Dialog', options)).appendTo("body");
        this.$el.modal({
            'backdrop': false,
            'keyboard': true,
        });
        if (options.size !== 'large'){
            var dialog_class_size = this.$dialog_box.find('.modal-lg').removeClass('modal-lg');
            if (options.size === 'small'){
                dialog_class_size.addClass('modal-sm');
            }
        }

        this.$el.appendTo(this.$dialog_box.find(".modal-body"));
        var $dialog_content = this.$dialog_box.find('.modal-content');
        if (options.dialogClass){
            $dialog_content.find(".modal-body").addClass(options.dialogClass);
        }
        $dialog_content.openerpClass();

        this.$dialog_box.on('hidden.bs.modal', this, function() {
            self.close();
        });
        this.$dialog_box.modal('show');

        this.dialog_inited = true;
        var res = this.start();
        return res;
    },
    /**
        Closes (hide) the popup, if destroy_on_close was passed to the constructor, it will be destroyed instead.
    */
    close: function(reason) {
        if (this.dialog_inited && !this.__tmp_dialog_hiding) {
            $('.tooltip').remove(); //remove open tooltip if any to prevent them staying when modal has disappeared
            if (this.$el.is(":data(bs.modal)")) {     // may have been destroyed by closing signal
                this.__tmp_dialog_hiding = true;
                this.$dialog_box.modal('hide');
                this.__tmp_dialog_hiding = undefined;
            }
            this.trigger("closing", reason);
        }
    },
    _closing: function() {
        if (this.__tmp_dialog_destroying)
            return;
        if (this.dialog_options.destroy_on_close) {
            this.__tmp_dialog_closing = true;
            this.destroy();
            this.__tmp_dialog_closing = undefined;
        }
    },
    /**
        Destroys the popup, also closes it.
    */
    destroy: function (reason) {
        this.$buttons.remove();
        _.each(this.getChildren(), function(el) {
            el.destroy();
        });
        if (! this.__tmp_dialog_closing) {
            this.__tmp_dialog_destroying = true;
            this.close(reason);
            this.__tmp_dialog_destroying = undefined;
        }
        if (this.dialog_inited && !this.isDestroyed() && this.$el.is(":data(bs.modal)")) {
            //we need this to put the instruction to remove modal from DOM at the end
            //of the queue, otherwise it might already have been removed before the modal-backdrop
            //is removed when pressing escape key
            var $element = this.$dialog_box;
            setTimeout(function () {
                //remove modal from list of opened modal since we just destroy it
                var modal_list_index = $.inArray($element, opened_modals);
                if (modal_list_index > -1){
                    opened_modals.splice(modal_list_index,1)[0].remove();
                }
                if (opened_modals.length > 0){
                    //we still have other opened modal so we should focus it
                    opened_modals[opened_modals.length-1].focus();
                    //keep class modal-open (deleted by bootstrap hide fnct) on body 
                    //to allow scrolling inside the modal
                    $('body').addClass('modal-open');
                }
            },0);
        }
        this._super();
    }
});

return Dialog;

});
