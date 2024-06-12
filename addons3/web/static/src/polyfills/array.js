if (!Array.prototype.at) {
    Object.defineProperty(Array.prototype, "at", {
        enumerable: false,
        value: function (index) {
            if (index >= 0) {
                return this[index];
            }
            return this[this.length + index];
        }
    });
}
