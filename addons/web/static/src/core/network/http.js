function checkResponseStatus(response) {
    if (response.status === 502) {
        throw new Error("Failed to fetch");
    }
    if (response.status === 413) {
        throw new Error("Content too large");
    }
}

export async function get(route, readMethod = "json") {
    const response = await fetch(route, { method: "GET" });
    checkResponseStatus(response);
    if (readMethod === "response") {
        return response;
    }
    return response[readMethod]();
}

export async function post(route, params = {}, readMethod = "json") {
    let formData = params;
    if (!(formData instanceof FormData)) {
        formData = new FormData();
        for (const key in params) {
            const value = params[key];
            if (Array.isArray(value) && value.length) {
                for (const val of value) {
                    formData.append(key, val);
                }
            } else {
                formData.append(key, value);
            }
        }
    }
    const response = await fetch(route, {
        body: formData,
        method: "POST",
    });
    checkResponseStatus(response);
    if (readMethod === "url") {
        return response.url;
    }
    if (readMethod === "response") {
        return response;
    }
    return response[readMethod]();
}
