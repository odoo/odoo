if (!Object.hasOwn) {
    Object.hasOwn = (obj, key) => Object.prototype.hasOwnProperty.call(obj, key);
}
