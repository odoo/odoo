odoo.define('wysiwyg.widgets', function (require) {
'use strict';

var Dialog = require('wysiwyg.widgets.Dialog');
var AltDialog = require('wysiwyg.widgets.AltDialog');
var MediaDialog = require('wysiwyg.widgets.MediaDialog');
var LinkDialog = require('wysiwyg.widgets.LinkDialog');
var ImageCropWidget = require('wysiwyg.widgets.ImageCropWidget');
const {ColorpickerDialog} = require('web.Colorpicker');

var media = require('wysiwyg.widgets.media');

return {
    Dialog: Dialog,
    AltDialog: AltDialog,
    MediaDialog: MediaDialog,
    LinkDialog: LinkDialog,
    ImageCropWidget: ImageCropWidget,
    ColorpickerDialog: ColorpickerDialog,

    MediaWidget: media.MediaWidget,
    SearchableMediaWidget: media.SearchableMediaWidget,
    FileWidget: media.FileWidget,
    ImageWidget: media.ImageWidget,
    DocumentWidget: media.DocumentWidget,
    IconWidget: media.IconWidget,
    VideoWidget: media.VideoWidget,
};
});
