import { expect, test } from "@odoo/hoot";
import { contains } from "@web/../tests/web_test_helpers";
import { defineWebsiteModels, dummyBase64Img, setupWebsiteBuilder } from "../website_helpers";
import { queryOne, waitFor } from "@odoo/hoot-dom";

defineWebsiteModels();

test("reorder carousel item should update container title", async () => {
    const { getEditor } = await setupWebsiteBuilder(
        `
        <section class="s_carousel_intro_wrapper p-0">
            <div class="s_carousel_intro s_carousel_default carousel carousel-dark" data-bs-ride="true" data-bs-interval="10000">
                <div class="carousel-inner">
                    <div class="s_carousel_intro_item carousel-item active" data-name="Slide">
                        <div class="container">
                            <div class="row o_grid_mode">
                                <div data-name="Block">
                                    <h1>Slide header 1</h1>
                                </div>
                                <div data-name="Block">
                                    <p class="lead">Slide</p>
                                </div>
                                <div class="o_grid_item o_grid_item_image" data-name="Block">
                                    <img src='${dummyBase64Img}' alt="" class="img img-fluid first_img">
                                </div>
                            </div>
                        </div>
                    </div>
                    <div class="s_carousel_intro_item carousel-item" data-name="Slide">
                        <div class="container">
                            <div class="row o_grid_mode">
                                <div data-name="Block">
                                    <h1>Slide header 2</h1>
                                </div>
                                <div data-name="Block">
                                    <p class="lead">slide 2</p>
                                </div>
                                <div class="o_grid_item o_grid_item_image" data-name="Block">
                                    <img src='${dummyBase64Img}' alt="" class="img img-fluid">
                                </div>
                            </div>
                        </div>
                    </div>
                    <div class="s_carousel_intro_item carousel-item" data-name="Slide">
                        <div class="container">
                            <div class="row o_grid_mode">
                                <div data-name="Block">
                                    <h1>Slide header 3</h1>
                                </div>
                                <div data-name="Block">
                                    <p class="lead">slide 3</p>
                                </div>
                                <div class="o_grid_item o_grid_item_image" data-name="Block">
                                    <img src='${dummyBase64Img}' alt="" class="img img-fluid">
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
                <div class="o_horizontal_controllers container o_not_editable" contenteditable="false">
                    <div class="o_horizontal_controllers_row row">
                        <div class="o_arrows_wrapper">
                            <button class="carousel-control-prev o_not_editable o_we_no_overlay" aria-label="Previous" title="Previous" contenteditable="false">
                                <span class="carousel-control-prev-icon" aria-hidden="true"></span>
                                <span class="visually-hidden">Previous</span>
                            </button>
                            <button class="carousel-control-next o_not_editable o_we_no_overlay" aria-label="Next" title="Next" contenteditable="false">
                                <span class="carousel-control-next-icon" aria-hidden="true"></span>
                                <span class="visually-hidden">Next</span>
                            </button>
                        </div>
                        <div class="s_carousel_indicators_numbers carousel-indicators o_we_no_overlay">
                            <button type="button" class="active" aria-label="Carousel indicator"></button>
                            <button type="button" aria-label="Carousel indicator"></button>
                            <button type="button" aria-label="Carousel indicator"></button>
                        </div>
                    </div>
                </div>
            </div>
        </section>
        `
    );
    const editor = getEditor();
    const builderOptions = editor.shared["builder-options"];
    const expectOptionContainerToInclude = (elem) => {
        expect(builderOptions.getContainers().map((container) => container.element)).toInclude(
            elem
        );
    };

    await contains(":iframe .first_img").click();
    await waitFor("[data-action-value='next']");
    expect("[data-container-title='Slide (1/3)']").toHaveCount(1);
    expect("[data-container-title='Slide (2/3)']").toHaveCount(0);
    expect("[data-container-title='Slide (3/3)']").toHaveCount(0);
    expect("[data-action-value='next']").toHaveCount(1);
    await contains("[data-action-value='next']").click();

    // the container title should be updated after reordering
    expectOptionContainerToInclude(queryOne(":iframe .first_img"));
    expect("[data-container-title='Slide (1/3)']").toHaveCount(0);
    expect("[data-container-title='Slide (2/3)']").toHaveCount(1);
    expect("[data-container-title='Slide (3/3)']").toHaveCount(0);

    expect("[data-action-value='next']").toHaveCount(1);
    await contains("[data-action-value='next']").click();

    expectOptionContainerToInclude(queryOne(":iframe .first_img"));
    expect("[data-container-title='Slide (1/3)']").toHaveCount(0);
    expect("[data-container-title='Slide (2/3)']").toHaveCount(0);
    expect("[data-container-title='Slide (3/3)']").toHaveCount(1);
});
