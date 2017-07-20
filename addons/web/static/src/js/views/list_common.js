odoo.define('web.list_common', function (require) {
"use strict";

var core = require('web.core');

var _t = core._t;
var Class = core.Class;

/**
 * @mixin Events
 */
var Events = /** @lends Events# */{
    /**
     * @param {String} event event to listen to on the current object, null for all events
     * @param {Function} handler event handler to bind to the relevant event
     * @returns this
     */
    bind: function (event, handler) {
        var calls = this['_callbacks'] || (this._callbacks = {});

        if (event in calls) {
            calls[event].push(handler);
        } else {
            calls[event] = [handler];
        }
        return this;
    },
    /**
     * @param {String} event event to unbind on the current object
     * @param {function} [handler] specific event handler to remove (otherwise unbind all handlers for the event)
     * @returns this
     */
    unbind: function (event, handler) {
        var calls = this._callbacks || {};
        if (!(event in calls)) { return this; }
        if (!handler) {
            delete calls[event];
        } else {
            var handlers = calls[event];
            handlers.splice(
                _(handlers).indexOf(handler),
                1);
        }
        return this;
    },
    /**
     * @param {String} event
     * @returns this
     */
    trigger: function (event) {
        var calls;
        if (!(calls = this._callbacks)) { return this; }
        var callbacks = (calls[event] || []).concat(calls[null] || []);
        for(var i=0, length=callbacks.length; i<length; ++i) {
            callbacks[i].apply(this, arguments);
        }
        return this;
    }
};
var Record = Class.extend(/** @lends Record# */{
    /**
     * @constructs Record
     * @extends instance.web.Class
     * 
     * @mixes Events
     * @param {Object} [data]
     */
    init: function (data) {
        this.attributes = data || {};
    },
    /**
     * @param {String} key
     * @returns {Object}
     */
    get: function (key) {
        return this.attributes[key];
    },
    /**
     * @param key
     * @param value
     * @param {Object} [options]
     * @param {Boolean} [options.silent=false]
     * @returns {Record}
     */
    set: function (key, value, options) {
        options = options || {};
        var old_value = this.attributes[key];
        if (old_value === value) {
            return this;
        }
        this.attributes[key] = value;
        if (!options.silent) {
            this.trigger('change:' + key, this, value, old_value);
            this.trigger('change', this, key, value, old_value);
        }
        return this;
    },
    /**
     * Converts the current record to the format expected by form views:
     *
     * .. code-block:: javascript
     *
     *    data: {
     *         $fieldname: {
     *             value: $value
     *         }
     *     }
     *
     *
     * @returns {Object} record displayable in a form view
     */
    toForm: function () {
        var form_data = {}, attrs = this.attributes;
        for(var k in attrs) {
            form_data[k] = {value: attrs[k]};
        }

        return {data: form_data};
    },
    /**
     * Converts the current record to a format expected by context evaluations
     * (identical to record.attributes, except m2o fields are their integer
     * value rather than a pair)
     */
    toContext: function () {
        var output = {}, attrs = this.attributes;
        for(var k in attrs) {
            var val = attrs[k];
            if (typeof val !== 'object') {
                output[k] = val;
            } else if (val instanceof Array) {
                output[k] = val.length > 0 ? val[0] : null;
            } else {
                throw new Error(_.str.sprintf(_t("Can't convert value %s to context"), val));
            }
        }
        return output;
    }
});
Record.include(Events);
var Collection = Class.extend(/** @lends Collection# */{
    /**
     * Smarter collections, with events, very strongly inspired by Backbone's.
     *
     * Using a "dumb" array of records makes synchronization between the
     * various serious 
     *
     * @constructs Collection
     * @extends instance.web.Class
     * 
     * @mixes Events
     * @param {Array} [records] records to initialize the collection with
     * @param {Object} [options]
     */
    init: function (records, options) {
        options = options || {};
        _.bindAll(this, '_onRecordEvent');
        this.length = 0;
        this.records = [];
        this._byId = {};
        this._proxies = {};
        this._key = options.key;
        this._parent = options.parent;

        if (records) {
            this.add(records);
        }
    },
    /**
     * @param {Object|Array} record
     * @param {Object} [options]
     * @param {Number} [options.at]
     * @param {Boolean} [options.silent=false]
     * @returns this
     */
    add: function (record, options) {
        options = options || {};
        var records = record instanceof Array ? record : [record];

        for(var i=0, length=records.length; i<length; ++i) {
            var instance_ = (records[i] instanceof Record) ? records[i] : new Record(records[i]);
            instance_.bind(null, this._onRecordEvent);
            this._byId[instance_.get('id')] = instance_;
            if (options.at === undefined || options.at === null) {
                this.records.push(instance_);
                if (!options.silent) {
                    this.trigger('add', this, instance_, this.records.length-1);
                }
            } else {
                var insertion_index = options.at + i;
                this.records.splice(insertion_index, 0, instance_);
                if (!options.silent) {
                    this.trigger('add', this, instance_, insertion_index);
                }
            }
            this.length++;
        }
        return this;
    },

    /**
     * Get a record by its index in the collection, can also take a group if
     * the collection is not degenerate
     *
     * @param {Number} index
     * @param {String} [group]
     * @returns {Record|undefined}
     */
    at: function (index, group) {
        if (group) {
            var groups = group.split('.');
            return this._proxies[groups[0]].at(index, groups.join('.'));
        }
        return this.records[index];
    },
    /**
     * Get a record by its database id
     *
     * @param {Number} id
     * @returns {Record|undefined}
     */
    get: function (id) {
        if (!_(this._proxies).isEmpty()) {
            var record = null;
            _(this._proxies).detect(function (proxy) {
                record = proxy.get(id);
                return record;
            });
            return record;
        }
        return this._byId[id];
    },
    /**
     * Builds a proxy (insert/retrieve) to a subtree of the collection, by
     * the subtree's group
     *
     * @param {String} section group path section
     * @returns {Collection}
     */
    proxy: function (section) {
        this._proxies[section] = new Collection(null, {
            parent: this,
            key: section
        }).bind(null, this._onRecordEvent);
        return this._proxies[section];
    },
    /**
     * @param {Array} [records]
     * @returns this
     */
    reset: function (records, options) {
        options = options || {};
        _(this._proxies).each(function (proxy) {
            proxy.reset();
        });
        this._proxies = {};
        _(this.records).invoke('unbind', null, this._onRecordEvent);
        this.length = 0;
        this.records = [];
        this._byId = {};
        if (records) {
            this.add(records);
        }
        if (!options.silent) {
            this.trigger('reset', this);
        }
        return this;
    },
    /**
     * Removes the provided record from the collection
     *
     * @param {Record} record
     * @param {Boolean} [options.silent=false]
     * @returns this
     */
    remove: function (record, options) {
        var index = this.indexOf(record);
        if (index === -1) {
            _(this._proxies).each(function (proxy) {
                proxy.remove(record);
            });
            return this;
        }

        record.unbind(null, this._onRecordEvent);
        this.records.splice(index, 1);
        delete this._byId[record.get('id')];
        this.length--;
        if (!options || !options.silent) {
            this.trigger('remove', record, this);
        }
        return this;
    },

    _onRecordEvent: function (event) {
        switch(event) {
        // don't propagate reset events
        case 'reset': return;
        case 'change:id':
            var record = arguments[1];
            var new_value = arguments[2];
            var old_value = arguments[3];
            // [change:id, record, new_value, old_value]
            if (this._byId[old_value] === record) {
                delete this._byId[old_value];
                this._byId[new_value] = record;
            }
            break;
        }
        this.trigger.apply(this, arguments);
    },

    // underscore-type methods
    find: function (callback) {
        var record;
        for(var section in this._proxies) {
            if (!this._proxies.hasOwnProperty(section)) {
                continue;
            }
            if ((record = this._proxies[section].find(callback))) {
                return record;
            }
        }
        for(var i=0; i<this.length; ++i) {
            record = this.records[i];
            if (callback(record)) {
                return record;
            }
        }
    },
    each: function (callback) {
        for(var section in this._proxies) {
            if (this._proxies.hasOwnProperty(section)) {
                this._proxies[section].each(callback);
            }
        }
        for(var i=0; i<this.length; ++i) {
            callback(this.records[i]);
        }
    },
    map: function (callback) {
        var results = [];
        this.each(function (record) {
            results.push(callback(record));
        });
        return results;
    },
    pluck: function (fieldname) {
        return this.map(function (record) {
            return record.get(fieldname);
        });
    },
    indexOf: function (record) {
        return _(this.records).indexOf(record);
    },
    succ: function (record, options) {
        options = options || {wraparound: false};
        var result;
        for(var section in this._proxies) {
            if (!this._proxies.hasOwnProperty(section)) {
                continue;
            }
            if ((result = this._proxies[section].succ(record, options))) {
                return result;
            }
        }
        var index = this.indexOf(record);
        if (index === -1) { return null; }
        var next_index = index + 1;
        if (options.wraparound && (next_index === this.length)) {
            return this.at(0);
        }
        return this.at(next_index);
    },
    pred: function (record, options) {
        options = options || {wraparound: false};

        var result;
        for (var section in this._proxies) {
            if (!this._proxies.hasOwnProperty(section)) {
                continue;
            }
            if ((result = this._proxies[section].pred(record, options))) {
                return result;
            }
        }

        var index = this.indexOf(record);
        if (index === -1) { return null; }
        var next_index = index - 1;
        if (options.wraparound && (next_index === -1)) {
            return this.at(this.length - 1);
        }
        return this.at(next_index);
    }
});
Collection.include(Events);

return {
    Events: Events,
    Record: Record,
    Collection: Collection
};

});
