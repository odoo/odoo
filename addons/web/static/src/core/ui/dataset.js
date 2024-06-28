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
    const newValue =
        key === undefined ? cacheObject(el) : el[el.data] && el[el.data][camelCase(key)];
    if (newValue) {
        return newValue;
    }

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

function cacheObject(owner) {
    let value = owner[owner.data];

    if (!value) {
        value = {};
        // We can accept data for non-element nodes in modern browsers,
        // but we should not, see trac-8335.
        // Always return an empty object.
        if (owner.nodeType === 1 || owner.nodeType === 9 || !+owner.nodeType) {
            // If it is a node unlikely to be stringify-ed or looped over
            // use plain assignment
            if (owner.nodeType) {
                owner[owner.data] = value;
                // Otherwise secure it in a non-enumerable property
                // configurable must be true to allow the property to be
                // deleted when data is removed
            } else {
                Object.defineProperty(owner, owner.data, {
                    value: value,
                    configurable: true,
                });
            }
        }
    }

    return value;
}

function setData(owner, key, value) {
    let prop;
    const cache = cacheObject(owner);
    // Handle: [ owner, key, value ] args
    // Always use camelCase key (gh-2257)
    if (typeof key === "string") {
        cache[camelCase(key)] = value;
        // Handle: [ owner, { properties } ] args
    } else {
        // Copy the properties one-by-one to the cache object
        for (prop in key) {
            cache[camelCase(prop)] = key[prop];
        }
    }
    return cache;
}

HTMLElement.prototype.getDataset = function (key, value) {
    if (!this.data) {
        let data = 1;
        this.data = `Odoo_${Math.random()}${data++}`.replace(/\./g, "");
    }

    if (value === undefined) {
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
    }
    return setData(this, key, value);
};
