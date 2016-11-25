odoo.define('web.sidebar.digital', function (require) {
'use strict';

var Sidebar = require('web.Sidebar');
var Document = require('document.document');

Sidebar.include({
	/**
     * @private
     * @override
     */
    _getAttachmentDomain: function () {
        var _super = this._super();
        _super.push(['product_downloadable', '=', false]);
        return _super;
    }
});

});
