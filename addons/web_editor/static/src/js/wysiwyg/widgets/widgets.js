odoo.define('wysiwyg.widgets', function (require) {
'use strict';

var Dialog = require('wysiwyg.widgets.Dialog');
var AltDialog = require('wysiwyg.widgets.AltDialog');
var MediaDialog = require('wysiwyg.widgets.MediaDialog');
var SelectOptionsDialog = require('wysiwyg.widgets.SelectOptionsDialog');
var LinkDialog = require('wysiwyg.widgets.LinkDialog');
var LinkTools = require('wysiwyg.widgets.LinkTools');
var ImageCropWidget = require('wysiwyg.widgets.ImageCropWidget');
const LinkPopoverWidget = require('@web_editor/js/wysiwyg/widgets/link_popover_widget')[Symbol.for("default")];
const SelectOptionsPopoverWidget = require('@web_editor/js/wysiwyg/widgets/select_options_popover_widget')[Symbol.for("default")];
const {ColorpickerDialog} = require('web.Colorpicker');

var media = require('wysiwyg.widgets.media');

return {
    Dialog: Dialog,
    AltDialog: AltDialog,
    MediaDialog: MediaDialog,
    SelectOptionsDialog: SelectOptionsDialog,
    LinkDialog: LinkDialog,
    LinkTools: LinkTools,
    ImageCropWidget: ImageCropWidget,
    LinkPopoverWidget: LinkPopoverWidget,
    SelectOptionsPopoverWidget: SelectOptionsPopoverWidget,
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
