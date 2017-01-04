odoo.define("web.domainUtils", function (require) {
"use strict";

var pyeval = require("web.pyeval");

function domainToString(domain) {
    if (_.isString(domain)) return domain;
    return JSON.stringify(domain || []).replace(/false/g, "False").replace(/true/g, "True");
}
function stringToDomain(domain) {
    if (!_.isString(domain)) return domain;
    return pyeval.eval("domain", domain || "[]");
}

return {
    domainToString: domainToString,
    stringToDomain: stringToDomain,
};
});
