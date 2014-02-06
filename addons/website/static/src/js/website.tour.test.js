(function () {
var scripts = [];
if (typeof openerp === "undefined") {
    scripts.push("/web/static/lib/qweb/qweb2.js");
    scripts.push("/web/static/lib/qweb/openerpframework.js");
}
if (typeof openerp === "undefined" || !openerp.website || !openerp.website.add_template_file)
    scripts.push("/website/static/src/js/website.js");
if (typeof openerp === "undefined" || !openerp.website.Tour)
    scripts.push("/website/static/src/js/website.tour.js");
if (typeof Tour === "undefined") {
    scripts.push("/website/static/lib/bootstrap-tour/bootstrap-tour.js");
}
for (var i in scripts) {
    if (typeof jQuery === "undefined") {
        throw new Error("jQuery not found.\nhref: " + window.location.href + "\n\n" + document.body.innerHTML);
    }
    jQuery.ajax({
        async: false,
        type: 'GET',
        data: null,
        url: scripts[i],
        dataType: "script",
        error: function (a,b,e) {throw e;}
    });
}
})();