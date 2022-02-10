odoo.define('wysiwyg.widgets.MediaDialog', function (require) {
'use strict';

var Dialog = require('wysiwyg.widgets.Dialog');


/**
 * Lets the user select a media. The media can be existing or newly uploaded.
 *
 * The media can be one of the following types: image, document, video or
 * font awesome icon (only existing icons).
 *
 * The user may change a media into another one depending on the given options.
 */
var MediaDialog = Dialog.extend({});

return MediaDialog;
});
