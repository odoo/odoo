odoo.define('website_slides.add.section', function (require) {
    'use strict';

    var publicWidget = require('web.public.widget');

    var SectionDialog = publicWidget.Widget.extend({
        template: 'website.slide.add.section',
        events: {
            'hidden.bs.modal': 'destroy',
            'click button.save': '_save',
            'click button[data-dismiss="modal"]': '_cancel',
            'change input#upload': '_slideUpload',
            'change input#url': '_slideUrl',
            'click .list-group-item': function (ev) {
                this.$('.list-group-item').removeClass('active');
                $(ev.target).closest('li').addClass('active');
            }
        },

        /**
         * @override
         * @param {Object} el
         * @param {number} channel_id
         */
        init: function (el, channelID) {
            this._super(el, channelID);
            this.channel_id = parseInt(channelID, 10);
            this.index_content = '';
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
        _getValue: function () {
            var canvas = this.$('#data_canvas')[0],
                values = {
                    'channel_id': this.channel_id || '',
                    'url': this.$('#url').val(),
                    'name': this.$('#section_name').val()
                };
            return values;
        },
        /**
         * @private
         */
        _validate: function () {
            this.$('.form-group').removeClass('o_has_error').find('.form-control, .custom-select').removeClass('is-invalid');
            if (!this.$('#name').val()) {
                this.$('#name').closest('.form-group').addClass('o_has_error').find('.form-control, .custom-select').addClass('is-invalid');
                return false;
            }
            var url = this.$('#url').val() ? this.is_valid_url : false;
            if (!(this.file.name || url)) {
                this.$('#url').closest('.form-group').addClass('o_has_error').find('.form-control, .custom-select').addClass('is-invalid');
                return false;
            }
            return true;
        },
        //--------------------------------------------------------------------------
        // Handlers
        //--------------------------------------------------------------------------

        /**
         * @override
         * @param {Object} ev
         */
        _save: function (ev) {
            var self = this;

            var values = this._getValue();
            if ($(ev.target).data('published')) {
                values.website_published = true;
            }
            this.$('.oe_slides_upload_loading').show();
            this.$('.modal-footer, .modal-body').hide();
            this._rpc({
                route: '/slides/add_category',
                params: values,
            }).then(function (data) {
                if (data.error) {
                    self._displayAlert(data.error);
                    self.$('.oe_slides_upload_loading').hide();
                    self.$('.modal-footer, .modal-body').show();

                } else {
                    window.location = data.url;
                }
            });
        },
        /**
         * @override
         */
        _cancel: function () {
            this.trigger('cancel');
        },

    });

    publicWidget.registry.websiteSlidesSection = publicWidget.Widget.extend({
        selector: '.oe_slide_js_add_section',
        xmlDependencies: ['/website_slides/static/src/xml/website_slides_upload.xml'],
        events: {
            'click': '_onAddSectionClick',
        },

        /**
         * @override
         */
        start: function () {
            // Automatically open the upload dialog if requested from query string
            if ($.deparam.querystring().enable_slide_upload !== undefined) {
                this._openDialog(this.$el.attr('channel_id'));
            }
            return this._super.apply(this, arguments);
        },

        //--------------------------------------------------------------------------
        // Private
        //--------------------------------------------------------------------------

        _openDialog: function (channelID) {
            new SectionDialog(this, channelID).appendTo(document.body);
        },

        //--------------------------------------------------------------------------
        // Handlers
        //--------------------------------------------------------------------------

        /**
         * @private
         * @param {Event} ev
         */
        _onAddSectionClick: function (ev) {
            console.log('test');
            this._openDialog($(ev.currentTarget).attr('channel_id'));
        },
    });
});
