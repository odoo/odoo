module.exports = {
    _data: {},
    add: function(name, func) {
        if (this._data.hasOwnProperty(name)) {
            //TODO warn
        }
        this._data[name] = func;
    },
    addMultiple: function(functions) {
        Object.keys(functions).forEach(
            function(name) {
                this.add(name, functions[name]);
            }.bind(this));
    },
    get: function(name) {
        return this._data[name];
    }
};
