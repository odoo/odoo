(function () {

function LoadScript(src) {
    xmlHttp = new XMLHttpRequest();
    xmlHttp.onreadystatechange = function() {
        if(xmlHttp.readyState == 4) {
            if (xmlHttp.status == 200 || xmlHttp.status == 304) {
                new Function(xmlHttp.responseText)();
            } else {
                throw new Error("Can't load JavaScript.\nhref: " + window.location.href + "\nsrc: " + src);
            }
        }
    };
    xmlHttp.open("GET", src, false);
    xmlHttp.setRequestHeader('Content-Type', 'application/x-www-form-urlencoded');
    xmlHttp.send(null);
}

if (typeof jQuery === "undefined")
    LoadScript("/web/static/lib/jquery/jquery.js");
if (typeof _ === "undefined")
    LoadScript("/web/static/lib/underscore/underscore.js");
if (typeof openerp === "undefined") {
    LoadScript("/web/static/lib/qweb/qweb2.js");
    LoadScript("/web/static/src/js/openerpframework.js");
}
if (typeof openerp === "undefined" || !openerp.website || !openerp.website.add_template_file)
    LoadScript("/website/static/src/js/website.js");
if (typeof Tour === "undefined")
    LoadScript("/website/static/lib/bootstrap-tour/bootstrap-tour.js");
if (typeof openerp === "undefined" || !openerp.website.Tour)
    LoadScript("/website/static/src/js/website.tour.js");

})();