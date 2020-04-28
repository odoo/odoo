odoo.define('website_sale.extra_product_media', function (require) {
"use strict";

const { qweb, _t } = require('web.core');
const Widget = require('web.Widget');
const weWidgets = require('wysiwyg.widgets');


const extraProductMedia = Widget.extend({
    xmlDependencies: ['/website_sale/static/src/xml/website_sale.xml'],
    placeholder: "/web/static/src/img/placeholder.png",
    events: {
        'dblclick': '_onClickUploadMedia',
    },

    /**
     * @override
     */
    start: function () {
        const def = this._super.apply(this, arguments);
        this.productMedias = [];
        this.currentIndex = this.$el.data('slide-to');
        this.productID = this.$el.data('product-id');
        this.isEnableCarouselControl = this.currentIndex === 1;
        $('.o_carousel_product_tooltip').tooltip();
        return def;
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     *
     * @private
     * @param {Object} params
     * @returns {Promise}
     *
     */
    _getProductThumbnailImageContent: function (params) {
        return this._rpc({
            route: '/shop/product/thumbnail_image/content',
            params: params
        });
    },
    /**
     * update carousel indicator and carousel inner item
     * while upload new image and video
     *
     * @private
     * @param {Object} values
     *
     */
    _updateCarouselIndicatorAndInnerItem: async function (values) {
        const result = await this._getProductThumbnailImageContent(values);
        if (result && result.error) {
            this.do_notify(_t('Error'), result.error, true);
        }
        if (result && !result.error && result.image_1920) {
            this.productMedias.push(result);
            values.index = this.currentIndex;
            if (result.video_url) {
                values.image_1920 = result.image_1920;
            }

            // carousel indicator
            const $newli = $(qweb.render('carouselIndicator', values));
            this.currentIndex = this.currentIndex + 1;
            this.$el.attr('data-slide-to', this.currentIndex);
            $newli.insertBefore(this.$el);

            // carousel inner item
            const $carousel = $('#product_detail #o-carousel-product .carousel-inner');
            let $newInnerItem = $(qweb.render('carouselInnerItem', values));
            $newInnerItem.appendTo($carousel);
            // enable carousel control while product variant image < 1
            // and insert new variant image using web_editor
            if (this.isEnableCarouselControl) {
                $(qweb.render('carouselControl')).insertAfter($carousel);
            }
            $newli.click();
        }
    },
    /**
     * save product extra image and video
     *
     * @private
     * @returns {Promise}
     *
     */
    _save: function () {
        return this._rpc({
            model: 'product.image',
            method: 'create',
            args: [this.productMedias],
        });
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * open media dialog for upload image and video
     *
     * @private
     * @param {MouseEvent} ev
     * @returns {Promise}
     *
     */
    _onClickUploadMedia: function (ev) {
        return new Promise(resolve => {
            const $image = $('<img>', {class: 'img img-responsive'});
            const mediaDialog = new weWidgets.MediaDialog(this, {
                noIcons: true,
                noDocuments: true,
            }, $image[0]).open();
            this._saving = false;
            mediaDialog.on('save', this, data => {
                let isVideoFrame= data.classList.contains('media_iframe_video');
                this._updateCarouselIndicatorAndInnerItem({
                    name: this.$el.data('product-name'),
                    product_tmpl_id: this.productID,
                    video_url: isVideoFrame ? data.dataset.oeExpression : '',
                    image_1920: isVideoFrame ? this.placeholder : data.src,
                });
                this._saving = true;
                resolve();
            });
            mediaDialog.on('closed', this, function () {
                if (!this._saving) {
                    resolve();
                }
            });
        });
    },
});
return extraProductMedia;
});
