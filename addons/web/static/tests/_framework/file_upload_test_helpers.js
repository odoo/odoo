import { EventBus } from "@odoo/owl";
import { mockService } from "./app_test_helpers";

/**
 * Mocks the `file_upload` service. `post(route, params)` receives the fields of
 * each request (the files in `ufile`) and returns its JSON response, as an
 * object or a string; a response with an `error` makes the upload fail.
 *
 * @param {(route: string, params: Object) => any} post
 */
export function mockUpload(post) {
    const bus = new EventBus();
    let nextId = 1;
    mockService("file_upload", {
        bus,
        uploads: {},
        upload(route, files, params = {}) {
            const data = new FormData();
            params.buildFormData?.(data);
            const upload = { id: nextId++, data, state: "pending", title: files[0]?.name };
            Promise.resolve(post(route, { ...Object.fromEntries(data), ufile: [...files] })).then(
                (response) => {
                    upload.response =
                        typeof response === "string" ? JSON.parse(response) : response;
                    upload.state = upload.response?.error ? "error" : "loaded";
                    // after the caller started to wait for the end of the upload
                    setTimeout(() =>
                        bus.trigger(
                            upload.state === "loaded" ? "FILE_UPLOAD_LOADED" : "FILE_UPLOAD_ERROR",
                            { upload }
                        )
                    );
                }
            );
            return upload;
        },
    });
}
