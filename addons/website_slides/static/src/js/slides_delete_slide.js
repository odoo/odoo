odoo.define('website_slides.delete.slide', function (require) {

    var sAnimations = require('website.content.snippets.animation');
    var core = require('web.core');
    var Widget = require('web.Widget');

    var _t = core._t;
    var QWeb = core.qweb;

    var DeleteSlideDialog = Widget.extend({
        template: 'website.slide.delete.slide',
        events: {
            'hidden.bs.modal': 'destroy',
            'click button[data-dismiss="modal"]': '_cancel',
            'click button.delete': '_delete'
        },

        /**
         * @override
         * @param {Object} el
         * @param {number} channel_id
         */
        init: function (el, slideID) {
            this._super(el, slideID);
            this.slide_id = parseInt(slideID, 10);
        },
        /**
         * @override
         */
        start: function () {
            this.$el.modal({
                backdrop: 'static'
            });
            return this._super.apply(this, arguments);
        },
        //--------------------------------------------------------------------------
        // Handlers
        //--------------------------------------------------------------------------
        _delete: function (ev) {
            var self = this;
            // TO FIX: CallBack is not executed
            $('[slide_id='+this.slide_id+']').remove();
            this._rpc({
                model: 'slide.slide',
                method: 'unlink',
                args: [[self.slide_id]],
            }).then(function () {
                $('[slide='+this.slide_id+']').remove();
            });
        },
        /**
         * @override
         */
        _cancel: function () {
            this.trigger('cancel');
        }
    });

    sAnimations.registry.websiteSlidesDeleteSlide = sAnimations.Class.extend({
        selector: '.oe_slide_js_delete_slide',
        xmlDependencies: ['/website_slides/static/src/xml/website_slides_upload.xml'],
        events: {
            'click': '_onDeleteSlideClick',
        },

        //--------------------------------------------------------------------------
        // Private
        //--------------------------------------------------------------------------

        _openDialog: function (slideID) {
            new DeleteSlideDialog(this, slideID).appendTo(document.body);
        },

        //--------------------------------------------------------------------------
        // Handlers
        //--------------------------------------------------------------------------

        /**
         * @private
         * @param {Event} ev
         */
        _onDeleteSlideClick: function (ev) {
            var target = $(ev.currentTarget);
            this._openDialog(target.attr('slide_id'));
        },
    });
    return DeleteSlideDialog;
    });
