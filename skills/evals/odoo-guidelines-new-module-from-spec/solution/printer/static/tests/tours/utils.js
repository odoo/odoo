/**
 * Mock the browser requests to /pstprnt or /cgi-bin/epos/service.cgi
 * These are requests to Zebra and ePOS printers.
 */
export function mockPrinterRequest(shouldThrow = false) {
    return {
        trigger: "body",
        run: async () => {
            const originalFetch = window.fetch;
            window.fetch = async (url, options) => {
                if (url.includes("/pstprnt")) {
                    if (shouldThrow) {
                        throw new Error("Mocked printer has been made unreachable");
                    }
                    const declaredLength = Number(options.headers?.["Content-Length"]);
                    const actualLength = options.body?.length ?? 0;
                    if (declaredLength !== actualLength) {
                        console.error(
                            `Content-Length header (${declaredLength}) does not match actual body length (${actualLength})`
                        );
                    }
                    const zpl = (options.body ?? "").trim();
                    if (!zpl.startsWith("^XA")) {
                        console.error(`ZPL does not start with ^XA: ${zpl.slice(0, 50)}`);
                    }
                    if (!zpl.endsWith("^XZ")) {
                        console.error(`ZPL does not end with ^XZ: ${zpl.slice(-50)}`);
                    }
                    return new Response("");
                }
                if (url.includes("/cgi-bin/epos/service.cgi")) {
                    if (shouldThrow) {
                        throw new Error("Mocked printer has been made unreachable");
                    }
                    const devid = new URL(url).searchParams.get("devid");
                    if (devid !== "local_printer") {
                        console.error(`Unexpected devid: expected 'local_printer', got '${devid}'`);
                    }
                    return new Response(`<response success="true" code=""/>`);
                }
                return originalFetch(url, options);
            };
        },
    };
}
