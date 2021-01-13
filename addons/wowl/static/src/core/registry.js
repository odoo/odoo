/** @odoo-module **/
const { core } = owl;
const { EventBus } = core;
/**
 * Registry
 *
 * The Registry class is basically just a mapping from a string key to an object.
 * It is really not much more than an object. It is however useful for the
 * following reasons:
 *
 * 1. it let us react and execute code when someone add something to the registry
 *   (for example, the FunctionRegistry subclass this for this purpose)
 * 2. it throws an error when the get operation fails
 * 3. it provides a chained API to add items to the registry.
 */
export class Registry extends EventBus {
  constructor() {
    super(...arguments);
    this.content = {};
  }
  /**
   * Add an entry (key, value) to the registry if key is not already used. If
   * the parameter force is set to true, an entry with same key (if any) is replaced.
   *
   * Note that this also returns the registry, so another add method call can
   * be chained
   */
  add(key, value, force = false) {
    if (!force && key in this.content) {
      throw new Error(`Cannot add '${key}' in this registry: it already exists`);
    }
    this.content[key] = value;
    const payload = { operation: "add", key, value };
    this.trigger("UPDATE", payload);
    return this;
  }
  /**
   * Get an item from the registry
   */
  get(key) {
    if (!(key in this.content)) {
      throw new Error(`Cannot find ${key} in this registry!`);
    }
    return this.content[key];
  }
  /**
   * Check the presence of a key in the registry
   */
  contains(key) {
    return key in this.content;
  }
  /**
   * Get a list of all elements in the registry
   */
  getAll() {
    return Object.values(this.content);
  }
  getEntries() {
    return Object.entries(this.content);
  }
  /**
   * Remove an item from the registry
   */
  remove(key) {
    const value = this.content[key];
    delete this.content[key];
    const payload = { operation: "delete", key, value };
    this.trigger("UPDATE", payload);
  }
}
