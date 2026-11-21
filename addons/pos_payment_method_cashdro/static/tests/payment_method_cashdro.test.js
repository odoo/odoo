import { beforeEach, describe, expect, mockFetch, test } from "@odoo/hoot";
import { PaymentMethodCashdro } from "@pos_payment_method_cashdro/payment_method_cashdro";
import { runTestScope } from "../../../web/static/tests/web_test_helpers";

describe.current.tags("headless");

const mockFetches = [];
const receivedRequests = [];

const cashdroMockFetch = (url) => {
    if (url === "/web/dataset/call_kw/pos.electronic.payment/init_payment_method") {
        return {
            result: {
                cashdro_ip: "mock-ip",
                cashdro_username: "mockUser",
                cashdro_password: "mockPassword",
                cashdro_use_lna: false,
            },
        };
    }

    const requestNum = receivedRequests.length;
    receivedRequests.push(url);

    if (mockFetches[requestNum]) {
        return mockFetches[requestNum](url);
    }

    console.error("Received fetch but no mock defined!");
};

const mockCashdroRequest = (operation, params, result = {}, code = 1) => {
    mockFetches.push((url) => {
        const parsedUrl = new URL(url);
        if (parsedUrl.host !== "mock-ip" || parsedUrl.pathname !== "/Cashdro3WS/index3.php") {
            console.error(`URL ${url} does not match expected`);
            return;
        }
        const queryParams = parsedUrl.searchParams;
        if (queryParams.get("operation") !== operation) {
            console.error(
                `Expected operation '${operation}', got '${queryParams.get("operation")}'`
            );
            return;
        }
        for (const [paramKey, paramValue] of Object.entries(params)) {
            if (queryParams.get(paramKey) !== paramValue) {
                console.error(
                    `Parameter '${paramKey}' does not match, expected '${paramValue}' but got '${queryParams.get(
                        paramKey
                    )}'`
                );
                return;
            }
        }

        expect.step(operation);

        if (result instanceof Error) {
            throw result;
        }

        return new Response(
            JSON.stringify({
                code,
                response: {
                    errorMessage: "none",
                    ...result,
                },
            })
        );
    });
    mockFetch(cashdroMockFetch);
};

beforeEach(() => {
    mockFetches.splice(0);
    receivedRequests.splice(0);
});

test("startPayment makes expected calls", async () => {
    const cashdro = await runTestScope(() => new PaymentMethodCashdro(1));
    mockCashdroRequest("askOperationExecuting", {
        name: "mockUser",
        password: "mockPassword",
    });
    mockCashdroRequest(
        "startOperation",
        {
            name: "mockUser",
            password: "mockPassword",
            type: "4",
            parameters: '{"amount":"500"}',
        },
        { operation: { operationId: "1234" } }
    );
    mockCashdroRequest("acknowledgeOperationId", {
        name: "mockUser",
        password: "mockPassword",
        operationId: "1234",
    });

    const result = await cashdro.startPayment(5.0, 1, {});

    expect(result.transaction_id).toBe("1234/1");
    expect(result.status).toBe("pending");
    expect.verifySteps(["askOperationExecuting", "startOperation", "acknowledgeOperationId"]);
});

test("startRefund makes expected calls", async () => {
    const cashdro = await runTestScope(() => new PaymentMethodCashdro(1));
    mockCashdroRequest("askOperationExecuting", {
        name: "mockUser",
        password: "mockPassword",
    });
    mockCashdroRequest(
        "startOperation",
        {
            name: "mockUser",
            password: "mockPassword",
            type: "3",
            parameters: '{"amount":"500"}',
        },
        { operation: { operationId: "1234" } }
    );
    mockCashdroRequest("acknowledgeOperationId", {
        name: "mockUser",
        password: "mockPassword",
        operationId: "1234",
    });

    const result = await cashdro.startRefund(5.0, 1, {});

    expect(result.transaction_id).toBe("1234/1");
    expect(result.status).toBe("pending");
    expect.verifySteps(["askOperationExecuting", "startOperation", "acknowledgeOperationId"]);
});

test("cancelTransaction makes expected calls", async () => {
    const cashdro = await runTestScope(() => new PaymentMethodCashdro(1));
    mockCashdroRequest("finishOperation", {
        name: "mockUser",
        password: "mockPassword",
        type: "2",
        operationId: "1234",
    });

    await cashdro._initPaymentMethod();
    await cashdro.cancelTransaction("1234/1");

    expect.verifySteps(["finishOperation"]);
});

test("getTransactionStatus with pending payment returns pending result", async () => {
    const cashdro = await runTestScope(() => new PaymentMethodCashdro(1));
    mockCashdroRequest(
        "askOperation",
        { name: "mockUser", password: "mockPassword", operationId: "1234" },
        { operation: { operation: { state: "E" } } }
    );

    await cashdro._initPaymentMethod();
    const result = await cashdro.getTransactionStatus("1234/1");

    expect(result.transaction_id).toBe("1234/1");
    expect(result.status).toBe("pending");
    expect.verifySteps(["askOperation"]);
});

test("getTransactionStatus with completed payment returns successful result", async () => {
    const cashdro = await runTestScope(() => new PaymentMethodCashdro(1));
    mockCashdroRequest(
        "askOperation",
        { name: "mockUser", password: "mockPassword", operationId: "1234" },
        { operation: { operation: { state: "F", totalin: "560", totalout: "50" } } }
    );

    await cashdro._initPaymentMethod();
    const result = await cashdro.getTransactionStatus("1234/1");

    expect(result.transaction_id).toBe("1234/1");
    expect(result.status).toBe("paid");
    expect(result.final_amount).toBe(5.1);
    expect.verifySteps(["askOperation"]);
});

test("getTransactionStatus with cancelled payment returns failed result", async () => {
    const cashdro = await runTestScope(() => new PaymentMethodCashdro(1));
    mockCashdroRequest(
        "askOperation",
        { name: "mockUser", password: "mockPassword", operationId: "1234" },
        { operation: { operation: { state: "F", totalin: "0", totalout: "0" } } }
    );

    await cashdro._initPaymentMethod();
    const result = await cashdro.getTransactionStatus("1234/1");

    expect(result.transaction_id).toBe("1234/1");
    expect(result.status).toBe("failed");
    expect.verifySteps(["askOperation"]);
});

test("Cashdro error responses are thrown", async () => {
    const cashdro = await runTestScope(() => new PaymentMethodCashdro(1));
    mockCashdroRequest(
        "askOperationExecuting",
        {
            name: "mockUser",
            password: "mockPassword",
        },
        { errorMessage: "Error message" },
        -1
    );

    await expect(cashdro.startPayment(5.0, 1, {})).rejects.toMatch("Error message");
    expect.verifySteps(["askOperationExecuting"]);
});

test("Network error responses are handled and thrown", async () => {
    const cashdro = await runTestScope(() => new PaymentMethodCashdro(1));
    mockCashdroRequest(
        "askOperationExecuting",
        {
            name: "mockUser",
            password: "mockPassword",
        },
        new TypeError()
    );

    await expect(cashdro.startPayment(5.0, 1, {})).rejects.toMatch(
        "Could not reach cash machine on the network, please check your IP and/or LNA settings."
    );
    expect.verifySteps(["askOperationExecuting"]);
});
