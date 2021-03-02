/** @odoo-module **/

import { NetworkErrorDialog, ServerErrorDialog } from "../errors/error_dialogs";
import OdooError from "../errors/odoo_error";
import parse from "./content_disposition";
import { download } from "./download";
import { serviceRegistry } from "../webclient/service_registry";

export const downloadService = {
  name: "download",
  deploy() {
    return async function (options) {
      return new Promise((resolve, reject) => {
        const xhr = new XMLHttpRequest();
        let data;
        if (options.hasOwnProperty("form")) {
          options = options;
          xhr.open(options.form.method, options.form.action);
          data = new FormData(options.form);
        } else {
          options = options;
          xhr.open("POST", options.url);
          data = new FormData();
          Object.entries(options.data).forEach((entry) => {
            const [key, value] = entry;
            data.append(key, value);
          });
        }
        data.append("token", "dummy-because-api-expects-one");
        if (odoo.csrf_token) {
          data.append("csrf_token", odoo.csrf_token);
        }
        // IE11 wants this after xhr.open or it throws
        xhr.responseType = "blob";
        xhr.onload = () => {
          const mimetype = xhr.response.type;
          if (xhr.status === 200 && mimetype !== "text/html") {
            // replace because apparently we send some C-D headers with a trailing ";"
            const header = (xhr.getResponseHeader("Content-Disposition") || "").replace(/;$/, "");
            const filename = header ? parse(header).parameters.filename : null;
            download(xhr.response, filename, mimetype);
            return resolve(filename);
          } else {
            const decoder = new FileReader();
            decoder.onload = () => {
              const contents = decoder.result;
              const doc = new DOMParser().parseFromString(contents, "text/html");
              const nodes =
                doc.body.children.length === 0 ? doc.body.childNodes : doc.body.children;
              const error = new OdooError("XHR_SERVER_ERROR");
              error.Component = ServerErrorDialog;
              try {
                // Case of a serialized Odoo Exception: It is Json Parsable
                const node = nodes[1] || nodes[0];
                error.message = "Serialized Python Exception";
                error.traceback = JSON.parse(node.textContent);
              } catch (e) {
                // Arbitrary uncaught python side exception
                error.message = "Arbitrary Uncaught Python Exception";
                error.traceback = `${xhr.status}
                          ${nodes.length > 0 ? nodes[0].textContent : ""}
                          ${nodes.length > 1 ? nodes[1].textContent : ""}
                      `;
              }
              reject(error);
            };
            decoder.readAsText(xhr.response);
          }
        };
        xhr.onerror = () => {
          const error = new OdooError("XHR_NETWORK_ERROR");
          error.Component = NetworkErrorDialog;
          reject(error);
        };
        xhr.send(data);
      });
    };
  },
};

serviceRegistry.add("download", downloadService);