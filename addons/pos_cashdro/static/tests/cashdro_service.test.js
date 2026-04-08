import { beforeEach, describe, expect, mockFetch, runAllTimers, test } from "@odoo/hoot";
import { CashdroService } from "@pos_cashdro/cashdro_service";

const mockFetches = [];
const receivedRequests = [];

const mockCashdroRequest = (operation, params, result = {}, code = 1) => {
    mockFetches.push((url) => {
        const parsedUrl = new URL(url);
        if (parsedUrl.host !== "mock-ip" || parsedUrl.pathname !== "/Cashdro3WS/index3.php") {
            console.error("URL does not match expected");
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
};

beforeEach(() => {
    mockFetches.splice(0);
    receivedRequests.splice(0);
    mockFetch((url) => {
        const requestNum = receivedRequests.length;
        receivedRequests.push(url);

        if (mockFetches[requestNum]) {
            return mockFetches[requestNum](url);
        }

        console.error("Received fetch but no mock defined!");
    });
});

describe("connect", () => {
    test("sets credentials", () => {
        const cashdroService = new CashdroService();

        cashdroService.connect("mock-ip", "mockUser", "mockPassword");

        expect(cashdroService.ip).toBe("mock-ip");
        expect(cashdroService.username).toBe("mockUser");
        expect(cashdroService.password).toBe("mockPassword");
    });

    test("resets state", () => {
        const cashdroService = new CashdroService();
        cashdroService.forceHttp = true;
        cashdroService.ip = "oldIp";

        cashdroService.connect("mock-ip", "mockUser", "mockPassword");

        expect(cashdroService.ip).toBe("mock-ip");
        expect(cashdroService.forceHttp).toBe(false);
    });
});

describe("sendPaymentRequest", () => {
    test("works correctly for successful payment", async () => {
        const cashdroService = new CashdroService();
        cashdroService.connect("mock-ip", "mockUser", "mockPassword");
        mockCashdroRequest(
            "startOperation",
            {
                name: "mockUser",
                password: "mockPassword",
                type: "4",
                parameters: '{"amount":"123"}',
            },
            { operation: { operationId: "1234" } }
        );
        mockCashdroRequest("acknowledgeOperationId", {
            name: "mockUser",
            password: "mockPassword",
            operationId: "1234",
        });

        const operationId = await cashdroService.sendPaymentRequest(123);

        expect(operationId).toBe("1234");
        expect.verifySteps(["startOperation", "acknowledgeOperationId"]);
    });

    test("throws error if Cashdro returns error", async () => {
        const cashdroService = new CashdroService();
        cashdroService.connect("mock-ip", "mockUser", "mockPassword");
        mockCashdroRequest(
            "startOperation",
            {
                name: "mockUser",
                password: "mockPassword",
                type: "4",
                parameters: '{"amount":"123"}',
            },
            { errorMessage: "Error message" },
            -1
        );

        await expect(cashdroService.sendPaymentRequest(123)).rejects.toMatch("Error message");
        expect.verifySteps(["startOperation"]);
    });
});

describe("waitForPaymentCompletion", () => {
    test("polls payment status until complete", async () => {
        const cashdroService = new CashdroService();
        cashdroService.connect("mock-ip", "mockUser", "mockPassword");

        mockCashdroRequest(
            "askOperation",
            { name: "mockUser", password: "mockPassword", operationId: "1234" },
            { operation: { operation: { state: "E" } } }
        );
        mockCashdroRequest(
            "askOperation",
            { name: "mockUser", password: "mockPassword", operationId: "1234" },
            { operation: { operation: { state: "E" } } }
        );
        mockCashdroRequest(
            "askOperation",
            { name: "mockUser", password: "mockPassword", operationId: "1234" },
            { operation: { operation: { state: "F" } } }
        );

        const resultPromise = cashdroService.waitForPaymentCompletion("1234");
        await runAllTimers();
        await runAllTimers();
        await runAllTimers();
        await resultPromise;

        expect.verifySteps(["askOperation", "askOperation", "askOperation"]);
    });
});

describe("cancelPayment", () => {
    test("works correctly for successful cancellation", async () => {
        const cashdroService = new CashdroService();
        cashdroService.connect("mock-ip", "mockUser", "mockPassword");
        mockCashdroRequest("finishOperation", {
            name: "mockUser",
            password: "mockPassword",
            type: "3",
            operationId: "1234",
        });

        await cashdroService.cancelPayment("1234");

        expect.verifySteps(["finishOperation"]);
    });

    test("throws error if Cashdro returns error", async () => {
        const cashdroService = new CashdroService();
        cashdroService.connect("mock-ip", "mockUser", "mockPassword");
        mockCashdroRequest(
            "finishOperation",
            {
                name: "mockUser",
                password: "mockPassword",
                type: "3",
                operationId: "1234",
            },
            { errorMessage: "Error message" },
            -1
        );

        await expect(cashdroService.cancelPayment("1234")).rejects.toMatch("Error message");
        expect.verifySteps(["finishOperation"]);
    });
});
