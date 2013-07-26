
(function() {

function declare($, _, QWeb) {
    var openerp = {};

    openerp.web = {};

    return openerp;
};

if (typeof(define) !== "undefined") { // amd
    define(["jquery", "underscore", "qweb"], declare);
} else {
    window.openerp = declare($, _, QWeb2);
}

})();