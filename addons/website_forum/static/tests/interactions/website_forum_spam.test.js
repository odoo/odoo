import { describe, expect, test } from "@odoo/hoot";
import { advanceTime, click, edit, fill, queryAll, tick } from "@odoo/hoot-dom";
import { Deferred } from "@odoo/hoot-mock";
import { startInteractions, setupInteractionWhiteList } from "@web/../tests/public/helpers";
import { onRpc } from "@web/../tests/web_test_helpers";

setupInteractionWhiteList("website_forum.website_forum_spam");
describe.current.tags("interaction_dev");

const template = (options = {}) => `
 <div id="wrap" class="o_wforum_wrapper o_wforum_moderation_queue">
    <div class="modal fade show modal_shown" id="markAllAsSpam" data-spam-ids="${options.spamIds ? "[1,2]" : ""}" style="display: block;">
        <div class="modal-dialog">
            <div class="modal-content">
                <div class="modal-body bg-100">
                    <div class="tab-content" id="o_tab_content_spam">
                        <div class="tab-pane fade active show" data-key="post_id" id="spam_character">
                            <input type="text" id="spamSearch" placeholder="Search..." title="Spam all post" class="search-query form-control oe_search_box mb-2">
                            <div class="post_spam"></div>
                        </div>
                    </div>
                </div>
                <div class="modal-footer justify-content-start">
                    <button type="button" class="btn btn-primary o_wforum_mark_spam">Mark as spam</button>
                    <a class="btn btn-sm btn-default o_wforum_select_all_spam" href="#" type="button">Select All</a>
                </div>
            </div>
        </div>
    </div>
 </div>
`;

test("spamIds returns empty array if dataset is empty", async () => {
    const { core } = await startInteractions(template());
    expect(core.interactions[0].interaction.spamIDs).toHaveLength(0);
});

test("keep last spam input search", async () => {
    await startInteractions(template({ spamIds: true }));

    const def = new Deferred();
    def.then(() => expect.step("rpc"));
    onRpc("forum.post", "search_read", async () => await def);
    await click("#spamSearch");
    await fill("coucou");
    await advanceTime(201); // debounced
    await edit("hello");
    await advanceTime(201); // debounced
    expect.verifySteps([]);
    def.resolve([{ content: "<div>hello</div>"}]);
    await tick();
    expect.verifySteps(["rpc"]);
    expect(".post_spam").toHaveText("hello");
});

test("select all checkboxes", async () => {
    await startInteractions(`
    <div id="wrap" class="o_wforum_wrapper o_wforum_moderation_queue">
        <div class="modal fade show modal_shown" id="markAllAsSpam" data-spam-ids="[1,2]" style="display: block;">
            <div class="modal-dialog">
                <div class="modal-content">
                    <div class="modal-body bg-100">
                        <div class="tab-content" id="o_tab_content_spam">
                            <div class="tab-pane fade active show" data-key="create_uid" id="spam_user" role="tabpanel" aria-labelledby="user-tab">
                                <form class="row">
                                    <div class="col-6">
                                        <div class="card mb-2">
                                            <div class="card-body py-2">
                                                <div class="form-check">
                                                    <input type="checkbox" class="form-check-input" value="2" id="user_2">
                                                    <label class="form-check-label" for="user_2">
                                                        <span class="d-inline">Mitchell Admin</span>
                                                    </label>
                                                </div>
                                            </div>
                                        </div>
                                    </div><div class="col-6">
                                        <div class="card mb-2">
                                            <div class="card-body py-2">
                                                <div class="form-check">
                                                    <input type="checkbox" class="form-check-input" value="6" id="user_6">
                                                    <label class="form-check-label" for="user_6">
                                                        <span class="d-inline">Marc Demo</span>
                                                    </label>
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                </form>
                            </div>
                        </div>
                    </div>
                    <div class="modal-footer justify-content-start">
                        <button type="button" class="btn btn-primary o_wforum_mark_spam">Mark as spam</button>
                        <a class="btn btn-sm btn-default o_wforum_select_all_spam" href="#" type="button">Select All</a>
                    </div>
                </div>
            </div>
        </div>
    </div>
    `);
    queryAll(".tab-pane input").forEach((el) => {
        expect(el).not.toBeChecked();
    });
    await click(".o_wforum_select_all_spam");
    queryAll(".tab-pane input").forEach((el) => {
        expect(el).toBeChecked();
    });
});
