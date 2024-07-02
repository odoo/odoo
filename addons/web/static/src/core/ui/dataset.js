/** @odoo-module **/

// Matches dashed string for camelizing
const rmsPrefix = /^-ms-/,
    rdashAlpha = /-([a-z])/g;
function fcamelCase(all, letter) {
    return letter.toUpperCase();
}

// Convert dashed to camelCase; used by the css and data modules
// Support: IE <=9 - 11, Edge 12 - 15
// Microsoft forgot to hump their vendor prefix (trac-9572)
function camelCase(string) {
    return string.replace(rmsPrefix, "ms-").replace(rdashAlpha, fcamelCase);
}

const rbrace = /^(?:\{[\w\W]*\}|\[[\w\W]*\])$/,
    rmultiDash = /[A-Z]/g;
function getData(data) {
    if (data === "true") {
        return true;
    }

    if (data === "false") {
        return false;
    }

    if (data === "null") {
        return null;
    }

    // Only convert to a number if it doesn't change the string
    if (data === +data + "") {
        return +data;
    }

    if (rbrace.test(data)) {
        return JSON.parse(data);
    }

    return data;
}

function dataAttr(el, key) {
    if (el.nodeType === 1) {
        const name = "data-" + key.replace(rmultiDash, "-$&").toLowerCase();
        let data = el.getAttribute(name);

        if (typeof data === "string") {
            try {
                data = getData(data);
                // eslint-disable-next-line no-unused-vars
            } catch (e) {
                /* empty */
            }
        } else {
            data = undefined;
        }
        return data;
    }
    return undefined;
}

HTMLElement.prototype.getDataset = function (key) {
    if (key === undefined) {
        const data = {};
        const attrs = this && this.attributes;
        if (this.nodeType === 1) {
            let i = attrs.length;
            while (i--) {
                // Support: IE 11 only
                // The attrs elements can be null (trac-14894)
                if (attrs[i]) {
                    let name = attrs[i].name;
                    if (name.indexOf("data-") === 0) {
                        name = camelCase(name.slice(5));
                        data[name] = dataAttr(this, name);
                    }
                }
            }
        }
        return data;
    }
    return dataAttr(this, key);
};
