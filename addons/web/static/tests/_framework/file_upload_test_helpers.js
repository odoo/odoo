import { onRpc } from "./mock_server/mock_server";

/**
 * Mocks the file uploads (the multipart requests). `post(route, params)`
 * receives the fields of each request (the files in `ufile`) and returns its
 * JSON response, as an object or a string, or a `Response` (e.g. an error
 * page); a response with an `error` makes the upload fail.
 *
 * @param {(route: string, params: Object) => any} post
 */
export function mockUpload(post) {
    onRpc("/*", async (request) => {
        if (!request.headers.get("Content-Type")?.startsWith("multipart/form-data")) {
            return;
        }
        const params = { ufile: [] };
        for (const [name, value] of await request.formData()) {
            if (name === "ufile") {
                params.ufile.push(value);
            } else if (name !== "csrf_token") {
                params[name] = value;
            }
        }
        const response = await post(new URL(request.url).pathname, params);
        if (response instanceof Response) {
            return response;
        }
        return new Response(
            typeof response === "string" ? response : JSON.stringify(response ?? {})
        );
    });
}
