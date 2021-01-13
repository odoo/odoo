/** @odoo-module **/
export class KeepLast {
  constructor() {
    this.id = 0;
  }
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
