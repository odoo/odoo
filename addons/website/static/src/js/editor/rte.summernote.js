odoo.define('website.rte.summernote', function (require) {
'use strict';

var core = require('web.core');
const rte = require('web_editor.rte');
require('web_editor.rte.summernote');

var eventHandler = $.summernote.eventHandler;
var renderer = $.summernote.renderer;
var tplIconButton = renderer.getTemplate().iconButton;
var _t = core._t;

var fn_tplPopovers = renderer.tplPopovers;
renderer.tplPopovers = function (lang, options) {
    var $popover = $(fn_tplPopovers.call(this, lang, options));
    $popover.find('.note-image-popover .btn-group:has([data-value="img-thumbnail"])').append(
        tplIconButton('fa fa-object-ungroup', {
            title: _t('Transform the picture (click twice to reset transformation)'),
            event: 'transform',
        }));
    return $popover;
};

$.summernote.pluginEvents.transform = function (event, editor, layoutInfo, sorted) {
    var $selection = layoutInfo.handle().find('.note-control-selection');
    var $image = $($selection.data('target'));

    if ($image.data('transfo-destroy')) {
        $image.removeData('transfo-destroy');
        return;
    }

    $image.transfo();

    var mouseup = function (event) {
        $('.note-popover button[data-event="transform"]').toggleClass('active', $image.is('[style*="transform"]'));
    };
    $(document).on('mouseup', mouseup);

    var mousedown = function (event) {
        if (!$(event.target).closest('.transfo-container').length) {
            $image.transfo('destroy');
            $(document).off('mousedown', mousedown).off('mouseup', mouseup);
        }
        if ($(event.target).closest('.note-popover').length) {
            $image.data('transfo-destroy', true).attr('style', ($image.attr('style') || '').replace(/[^;]*transform[\w:]*;?/g, ''));
        }
        $image.trigger('content_changed');
    };
    $(document).on('mousedown', mousedown);
};

var fn_boutton_update = eventHandler.modules.popover.button.update;
eventHandler.modules.popover.button.update = function ($container, oStyle) {
    fn_boutton_update.call(this, $container, oStyle);
    $container.find('button[data-event="transform"]')
        .toggleClass('active', $(oStyle.image).is('[style*="transform"]'))
        .toggleClass('d-none', !$(oStyle.image).is('img'));
};

rte.Class.include({
    /**
     * @override
     */
    async start() {
        const res = await this._super(...arguments);

        // TODO review in master. This stable fix restores the possibility to
        // edit the company team snippet images on subsequent editions. Indeed
        // this badly relies on the contenteditable="true" attribute being on
        // those images but it is rightfully lost after the first save.
        // grep: COMPANY_TEAM_CONTENTEDITABLE
        this.__$editable.find('.s_company_team .o_not_editable img').prop('contenteditable', true);

        return res;
    },
});
});
