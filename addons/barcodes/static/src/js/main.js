
openerp.barcodes = function(instance) {
    "use strict";

    instance.barcode_reader = {};
    var module = instance.barcode_reader;

    openerp_barcode_reader(instance,module);         // import barcodes.js
};
