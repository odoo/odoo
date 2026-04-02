import { DocClient } from "@api_doc/doc_client";
import { mockDocIndex, mockDocModel } from "./doc_test_helpers";
import { queryAll, queryAllTexts } from "@odoo/hoot-dom";
import {
    animationFrame,
    expect,
    test,
    waitFor
} from "@odoo/hoot";

import {
    contains,
    mountWithCleanup,
    onRpc,
    patchWithCleanup,
} from "@web/../tests/web_test_helpers";

function setupMockModel(modelNames) {
    onRpc("/doc/index.json", () => {
        return mockDocIndex(modelNames);
    });
    modelNames.forEach((modelName) => {
        onRpc(`/doc/${modelName}.json`, () => {
            const model = mockDocModel(modelName);
            return model;
        });
    });
}

async function setupDocModel(index=0, modelNames=["M1", "M2", "M3"]) {
    setupMockModel(modelNames);
    const docClient = await mountWithCleanup(DocClient, {});
    await waitFor(".o-doc-sidebar-content div a");
    await contains(`.o-doc-sidebar-content div a:eq(${index})`).click();
    await contains(".o-doc-model-aside .o-doc-module-checks").click();
    await waitFor(".o-doc-method");
    return docClient;
}
function getCodeEditorDomValue(target="") {
    return queryAll(`${target} .ace_line`)
        .map((root) => queryAllTexts(`:scope > span`, { root }).join(""))
        .join("\n");
}

// ---- Tests ----

test.tags("desktop")
test("Simple test, load sidebar and aside", async () => {
    setupMockModel(["M1", "M2", "M3"]);
    await mountWithCleanup(DocClient, {});
    await animationFrame();
    // Check sidebar contains all models
    expect(".o-doc-sidebar-content div a").toHaveCount(3);
    expect(".o-doc-sidebar-content div a:eq(0)").toHaveText("Model_M1\nM1");
    expect(".o-doc-sidebar-content div a:eq(1)").toHaveText("Model_M2\nM2");
    expect(".o-doc-sidebar-content div a:eq(2)").toHaveText("Model_M3\nM3");
    await contains(".o-doc-sidebar-content div a:eq(0)").click();
    expect(".o-doc-model h2").toHaveText("Model_M1");
    // Check aside contains module and methods
    expect(".o-doc-model-aside .o-doc-module-checks").toHaveText("test_module");
    await contains(".o-doc-model-aside .o-doc-module-checks").click();
    // Select/Deselect + methods
    await waitFor(".o-doc-model-aside .o-doc-aside-methods")
    expect(".o-doc-model-aside .o-doc-aside-methods").toHaveCount(2);
    expect(".o-doc-model-aside .o-doc-aside-methods:eq(0)").toHaveText("method_1_M1");
    expect(".o-doc-model-aside .o-doc-aside-methods:eq(1)").toHaveText("method_2_M1");
});

test.tags("desktop")
test("Methods are parsed properly", async () => {
    await setupDocModel();
    // Headers
    expect(".o-doc-method").toHaveCount(2);
    expect(".o-doc-method:eq(0) .o-doc-method-header").toHaveText("method_1_M1\n#\ntest_module");
    expect(".o-doc-method:eq(1) .o-doc-method-header").toHaveText("method_2_M1\n#\ntest_module");
    expect(`.o-doc-method-header:eq(0) a`).toHaveAttribute("href", "#method_1_M1");
    expect(`.o-doc-method-header:eq(1) a`).toHaveAttribute("href", "#method_2_M1");
    await contains(".o-doc-method:eq(1) .o-doc-method-header").click();
    // Route + Return Type
    expect(".o-doc-method pre").toHaveCount(2);
    expect(".o-doc-method pre:eq(0)").toHaveText("/json/2/M1/method_1_M1");
    expect(".o-doc-method pre:eq(1)").toHaveText("None");
    // Inner and return docstring
    expect(".o-doc-method .doc_method_description").toHaveCount(2);
    expect(".o-doc-method .doc_method_description:eq(0)").toHaveText("This is a method.");
    expect(".o-doc-method .doc_method_description:eq(1)").toHaveText("Some return doc");
    // Parameters
    expect(".o-doc-method .o-doc-table tr").toHaveCount(3);
    expect(".o-doc-method .o-doc-table tr:eq(1)").toHaveText("param_a list[int] null");
    expect(".o-doc-method .o-doc-table tr:eq(2)").toHaveText("param_b int null");
});

test.tags("desktop")
test("Fields are parsed properly", async () => {
    await setupDocModel();
    expect(".o-doc-table").toHaveCount(4, {
        message: "There should be 4 'o-doc-table': model name + fields + 2 method parameters"
    });
    expect(".o-doc-table:eq(1) tr").toHaveCount(3);
    expect(".o-doc-table:eq(1) tr:eq(1) td").toHaveCount(6);

    const firstRow = ["field_1_M1", "string", "Field 1 M1", "optional", "", "test_module"];
    const secondRow = ["field_2_M1", "boolean", "Field 2 M1", "optional", "", "test_module"];

    firstRow.forEach((value, index) => {
        expect(`.o-doc-table:eq(1) tr:eq(1) td:eq(${index})`).toHaveText(value);
    });
    secondRow.forEach((value, index) => {
        expect(`.o-doc-table:eq(1) tr:eq(2) td:eq(${index})`).toHaveText(value);
    });
});

test.tags("desktop")
test("Request editor", async () => {
    await setupDocModel();
    expect(".ace_layer.ace_text-layer").toHaveCount(2);
    await contains(".o-doc-method:eq(1) .o-doc-method-header").click();

    expect(getCodeEditorDomValue()).toBe(`{\n"context"{},\n"param_a",\n"param_b"\n}`);

    await contains(".o_doc_request select").select("javascript");
    await animationFrame();
    expect(getCodeEditorDomValue()).toEqual(
        `(async()=>{
        // You MUST store this key securely. Place it in an
        // environment variable or in in a file outside of
        // git (e.g. your home directory).
        constapiKey="YOUR_API_KEY";

        constrequest={
        method:"POST",
        headers:{
        "Content-Type":"application/json",
        "Authorization":"Bearer "+apiKey,
        // "X-Odoo-Database": "...",
        },
        body:JSON.stringify({
        context:{},
        param_a:null,
        param_b:null
        }),
        };

        constresponse=awaitfetch("${window.location.origin}/json/2/M1/method_1_M1",request);
        if(response.ok){
        constdata=awaitresponse.json();
        console.log(data)
        }else{
        // Handle errors
        }
        })();`.replace(/  +/g, "")
    );
});

test.tags("desktop")
test("Generate api key hyperlink", async () => {
    patchWithCleanup(window, {
        open: (...args) => {
            expect.step(`callWindowOpen ${args[0]}`);
        }
    });
    await setupDocModel();

    expect("header div button").toHaveCount(2);
    await contains("header div button:eq(0)").click();

    expect(".modal a").toHaveText("Generate a new API key here");
    await contains(".modal a").click();

    await expect.waitForSteps([
        `callWindowOpen ${window.location.origin}/odoo/action-doc_api_key_wizard`
    ]);
});

test.tags("desktop")
test("Run request and get rpc error", async () => {
    patchWithCleanup(window, {
        open: (...args) => {
            expect.step(`callWindowOpen ${args[0]}`);
        }
    });
    await setupDocModel();

    expect("header div button").toHaveCount(2);
    await contains("header div button:eq(0)").click();

    expect(".modal a").toHaveText("Generate a new API key here");
    await contains(".modal input").edit("meow");
    await contains(".modal div button").click();

    await contains(".o_doc_request button").click();
    expect(getCodeEditorDomValue(".o-doc-code-editor:eq(1)")).toEqual(
        `{
        "error"{
        "name""RPC_ERROR",
        "type""server",
        "code"200,
        "data"{
        "name""MockServerError",
        "message""Unimplemented server route: /json/2/M1/method_1_M1"
        },
        "exceptionName""MockServerError",
        "subType""MockServerError",
        "message""Unimplemented server route: /json/2/M1/method_1_M1"
        }
        }`.replace(/  +/g, "")
    );
});

test.tags("desktop")
test("Search for model", async () => {
    await setupDocModel();
    expect(".o-doc-sidebar-content a").toHaveCount(3);
    expect(queryAllTexts(".o-doc-sidebar-content a", { inline: true })).toEqual([
        "Model_M1 M1",
        "Model_M2 M2",
        "Model_M3 M3"
    ]);

    await contains(".o-doc-sidebar input").edit("M2");
    expect(".o-doc-sidebar-content a").toHaveCount(1);
    expect(queryAllTexts(".o-doc-sidebar-content a", { inline: true })).toEqual(["Model_M2 M2"]);
});
