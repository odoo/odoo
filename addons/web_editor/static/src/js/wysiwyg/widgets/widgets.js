odoo.define('wysiwyg.widgets', function (require) {
'use strict';

var Dialog = require('wysiwyg.widgets.Dialog');
var AltDialog = require('wysiwyg.widgets.AltDialog');
var LinkDialog = require('wysiwyg.widgets.LinkDialog');
var LinkTools = require('wysiwyg.widgets.LinkTools');
var ImageCropWidget = require('wysiwyg.widgets.ImageCropWidget');
const LinkPopoverWidget = require('@web_editor/js/wysiwyg/widgets/link_popover_widget')[Symbol.for("default")];
const {ColorpickerDialog} = require('web.Colorpicker');

return {
    Dialog: Dialog,
    AltDialog: AltDialog,
    LinkDialog: LinkDialog,
    LinkTools: LinkTools,
    ImageCropWidget: ImageCropWidget,
    LinkPopoverWidget: LinkPopoverWidget,
    ColorpickerDialog: ColorpickerDialog,
};
});
