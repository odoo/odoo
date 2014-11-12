
openerp.barcodes = function(instance) {
    "use strict";

    instance.barcode_parser = {};
    var module = instance.barcode_parser;

    openerp_barcode_parser(instance,module);         // import barcodes.js
};
