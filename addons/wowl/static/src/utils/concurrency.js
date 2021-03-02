/** @odoo-module **/

/**
 * KeepLast is a concurrency primitive that manages a list of tasks, and only
 * keep the last task active.
 */
export class KeepLast {
  id = 0;

  /**
   * Register a new task
   *
   * @template T
   * @param {Promise<T>} promise
   * @returns {Promise<T>}
   */
  add(promise) {
    this.id++;
    const currentId = this.id;
    return new Promise((resolve, reject) => {
      promise
        .then((value) => {
          if (this.id === currentId) {
            resolve(value);
          }
        })
        .catch((reason) => {
          // not sure about this part
          if (this.id === currentId) {
            reject(reason);
          }
        });
    });
  }
}
