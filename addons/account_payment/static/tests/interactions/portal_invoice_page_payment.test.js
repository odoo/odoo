import {
    startInteractions,
    setupInteractionWhiteList,
} from "@web/../tests/public/helpers";

import { describe, expect, test } from "@odoo/hoot";
import { advanceTime, queryOne } from "@odoo/hoot-dom";

setupInteractionWhiteList("account_payment.portal_invoice_page_payment");

describe.current.tags("interaction_dev");

test("portal_invoice_page_payment is not started without #portal_pay", async () => {
    const { core } = await startInteractions("");
    expect(core.interactions).toHaveLength(0);
});

test("portal_invoice_page_payment is started with #portal_pay", async () => {
    const { core } = await startInteractions(`
    <div id="wrapwrap" class="o_portal">
        <header style="height: 50px;"></header>
        <main>
            <div class="container mt-3">
                <div class="alert alert-info alert-dismissible fade show d-print-none css_editable_mode_hidden">
                    <div class="text-center">
                        This is a preview of the customer portal.
                        <a class="alert-link" href="/odoo/action-account.action_move_out_invoice_type/2"><i class="oi oi-arrow-right me-1"></i>Back to edit mode</a>
                    </div>
                    <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close" data-oe-model="ir.ui.view" data-oe-id="540" data-oe-field="arch" data-oe-xpath="/t[1]/button[1]"></button>
                </div>
            </div>
            <div class="o_portal container mt-3">
                <div class="d-flex justify-content-between align-items-center flex-wrap">
                    <ol class="o_portal_submenu breadcrumb mb-0 flex-grow-1 px-0">
                        <li class="breadcrumb-item ms-1" data-oe-model="ir.ui.view" data-oe-id="539" data-oe-field="arch" data-oe-xpath="/t[1]/ol[1]/li[1]"><a href="/my/home" aria-label="Home" title="Home"><i class="fa fa-home"></i></a></li>
                        <li class="breadcrumb-item">
                            <a data-oe-model="ir.ui.view" data-oe-id="786" data-oe-field="arch" data-oe-xpath="/data/xpath/li[1]/a[1]" href="/my/invoices?access_token=48b81433-0b2f-4ebd-847b-980120176bb6&amp;payment=True">Invoices &amp; Bills</a>
                        </li>
                        <li class="breadcrumb-item active">
                            INV/2025/00002
                        </li>
                    </ol>
                    <div class="record_pager btn-group" role="group">
                        <a role="button" data-oe-model="ir.ui.view" data-oe-id="556" data-oe-field="arch" data-oe-xpath="/t[1]/t[1]/div[1]/a[1]" class="btn btn-light" href="/my/invoices/13?access_token=0bccb494-a155-43f2-9832-fe163a740edb"><i class="oi oi-chevron-left" role="img" aria-label="Previous" title="Previous"></i></a>
                        <a role="button" data-oe-model="ir.ui.view" data-oe-id="556" data-oe-field="arch" data-oe-xpath="/t[1]/t[1]/div[1]/a[2]" class="btn btn-light" href="/my/invoices/14?access_token=bd2e4e49-a208-4a8d-aec1-9b2286d437a8"><i class="oi oi-chevron-right" role="img" aria-label="Next" title="Next"></i></a>
                    </div>
                </div>
            </div>
            <div id="wrap" class="o_portal_wrap">
                <div class="container pt-3 pb-5">
                    <div class="container o_portal_sidebar">
                        <div class="row o_portal_invoice_sidebar">
                            <div class="d-flex col-lg-4 col-xxl-3 d-print-none">
                                <div class="o_portal_sidebar_content flex-grow-1 mb-4 mb-lg-0 pe-lg-4" id="sidebar_content">
                                    <div class="position-relative d-flex align-items-center justify-content-md-center justify-content-lg-between flex-wrap gap-2">
                                        <h2 class="mb-0 text-break mx-auto">
                                            <span data-oe-xpath="/data/xpath/div/t[1]/t[2]/h2[1]/span[1]" data-oe-model="account.move" data-oe-id="2" data-oe-field="amount_total" data-oe-type="monetary" data-oe-expression="invoice.amount_total" data-oe-readonly="1">$&nbsp;<span class="oe_currency_value">48,012.50</span></span>
                                        </h2>
                                        <div class="my-1 w-100">
                                        </div>
                                        <div class="small w-100 text-center">
                                            <i class="fa fa-clock-o" data-oe-model="ir.ui.view" data-oe-id="789" data-oe-field="arch" data-oe-xpath="/data/xpath/div/t[1]/t[2]/div[2]/i[1]"></i>
                                            <span class="o_portal_sidebar_timeago ml4" data-oe-model="ir.ui.view" data-oe-id="789" data-oe-field="arch" data-oe-xpath="/data/xpath/div/t[1]/t[2]/div[2]/span[1]" datetime="2025-01-06">Due today</span>
                                        </div>
                                    </div>
                                    <div class="d-flex flex-column gap-4 mt-3">
                                        <div class="d-flex flex-column gap-2">
                                            <a href="#" class="btn btn-primary" data-bs-toggle="modal" data-bs-target="#pay_with" data-oe-id="868" data-oe-xpath="/data/xpath[2]/a" data-oe-model="ir.ui.view" data-oe-field="arch">
                                            <i class="fa fa-fw fa-arrow-circle-right"></i> Pay Now
                                            </a>
                                            <div class="o_download_pdf d-flex flex-lg-column flex-xl-row flex-wrap gap-2">
                                                <a class="btn btn-light o_download_btn flex-grow-1" title="Download" role="button" data-oe-model="ir.ui.view" data-oe-id="789" data-oe-field="arch" data-oe-xpath="/data/xpath/div/t[1]/t[3]/div[1]/div[1]/div[1]/a[1]" href="/my/invoices/2?access_token=48b81433-0b2f-4ebd-847b-980120176bb6&amp;report_type=pdf&amp;download=true">
                                                <i class="fa fa-download"></i> Download
                                                </a>
                                            </div>
                                        </div>
                                    </div>
                                    <div class="d-none d-lg-block mt-5 small text-center text-muted" data-oe-model="ir.ui.view" data-oe-id="549" data-oe-field="arch" data-oe-xpath="/t[1]/div[1]/div[1]/div[2]">
                                        Powered by <a target="_blank" href="http://www.odoo.com?utm_source=db&amp;utm_medium=portal" title="odoo"><img src="/web/static/img/logo.png" alt="Odoo Logo" height="15" loading="lazy" style=""></a>
                                    </div>
                                </div>
                                <div class="vr d-none d-lg-block bg-300" data-oe-model="ir.ui.view" data-oe-id="549" data-oe-field="arch" data-oe-xpath="/t[1]/div[1]/div[2]"></div>
                            </div>
                            <div id="invoice_content" class="o_portal_content col-12 col-lg-8 col-xxl-9">
                                <div id="portal_pay" data-payment="True">
                                    <div class="row">
                                        <div class="modal fade modal_shown" id="pay_with" style="display: none;" aria-hidden="true">
                                            <div class="modal-dialog">
                                                <div class="modal-content">
                                                    <div class="modal-header pb-0" data-oe-model="ir.ui.view" data-oe-id="866" data-oe-field="arch" data-oe-xpath="/t[1]/div[1]/div[1]/div[1]/div[1]/div[1]">
                                                        <h3 class="modal-title">Pay</h3>
                                                        <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                                                    </div>
                                                    <div class="modal-body">
                                                        <div class="text-bg-light row row-cols-1 row-cols-md-2 mx-0 mb-3 py-2 rounded">
                                                            <div class="col my-3 text-break">
                                                                <label class="d-block small opacity-75" for="o_payment_summary_amount_full">Amount</label>
                                                                <span class="fs-5 fw-bold" id="o_payment_summary_amount_full" data-oe-type="monetary" data-oe-expression="value">$&nbsp;<span class="oe_currency_value">48,012.50</span></span>
                                                            </div>
                                                            <hr class="d-md-none m-0 text-300 opacity-100" data-oe-model="ir.ui.view" data-oe-id="622" data-oe-field="arch" data-oe-xpath="/t[1]/hr[1]">
                                                            <div class="col my-3 text-break o_payment_summary_separator">
                                                                <label class="d-block small opacity-75" for="o_payment_summary_reference_full">Reference</label>
                                                                <span class="fs-5 fw-bold" id="o_payment_summary_reference_full" data-oe-type="string" data-oe-expression="value">INV/2025/00002</span>
                                                            </div>
                                                        </div>
                                                        <div class="alert alert-warning mt-2">
                                                            <div data-oe-model="ir.ui.view" data-oe-id="612" data-oe-field="arch" data-oe-xpath="/t[1]/div[1]/div[1]">
                                                                <strong>No payment method available</strong>
                                                            </div>
                                                            <div class="mt-2">
                                                                <p data-oe-model="ir.ui.view" data-oe-id="612" data-oe-field="arch" data-oe-xpath="/t[1]/div[1]/div[2]/p[2]">
                                                                    No payment providers are configured.
                                                                </p>
                                                                <a
                                                                    name="activate_payment_provider"
                                                                    href="/odoo/action-payment.action_start_payment_onboarding"
                                                                    role="button"
                                                                    class="btn btn-primary me-2 d-none"
                                                                    data-oe-model="ir.ui.view"
                                                                    data-oe-id="612"
                                                                    data-oe-field="arch"
                                                                    data-oe-xpath="/t[1]/div[1]/div[2]/a[1]"
                                                                 >
                                                                     ACTIVATE <t t-out="onboarding_provider.upper()"/>
                                                                </a>
                                                                <a role="button" type="action" class="btn-link alert-warning me-2" href="/odoo/action-payment.action_payment_provider" data-oe-model="ir.ui.view" data-oe-id="612" data-oe-field="arch" data-oe-xpath="/t[1]/div[1]/div[2]/a[3]">
                                                                <strong><i class="oi oi-arrow-right"></i> Payment Providers</strong>
                                                                </a>
                                                            </div>
                                                        </div>
                                                        <script type="text/javascript" src="https://js.stripe.com/v3/" data-oe-model="ir.ui.view" data-oe-id="1709" data-oe-field="arch" data-oe-xpath="/t[1]/script[1]"></script>
                                                    </div>
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                                <div class="o_portal_html_view position-relative bg-white shadow p-3 overflow-hidden">
                                    <div class="o_portal_html_loader text-center" data-oe-model="ir.ui.view" data-oe-id="789" data-oe-field="arch" data-oe-xpath="/data/xpath/div/div[1]/div[1]/div[1]">
                                        <i class="fa fa-circle-o-notch fa-spin fa-2x fa-fw text-black-50"></i>
                                    </div>
                                    <iframe id="invoice_html" class="position-relative my-2" width="100%" height="100%" frameborder="0" scrolling="no" data-oe-model="ir.ui.view" data-oe-id="789" data-oe-field="arch" data-oe-xpath="/data/xpath/div/div[1]/div[1]/iframe[1]" src="/my/invoices/2?access_token=48b81433-0b2f-4ebd-847b-980120176bb6&amp;report_type=html" style="height: 0px;"></iframe>
                                </div>
                                <div id="invoice_communication" class="mt-4">
                                    <h3 data-oe-model="ir.ui.view" data-oe-id="789" data-oe-field="arch" data-oe-xpath="/data/xpath/div/div[1]/div[2]/h3[1]">Communication history</h3>
                                    <div id="discussion" data-anchor="true" class="d-print-none o_portal_chatter o_not_editable p-0" data-oe-model="ir.ui.view" data-oe-id="559" data-oe-field="arch" data-oe-xpath="/t[1]/div[1]" data-token="48b81433-0b2f-4ebd-847b-980120176bb6" data-res_model="account.move" data-res_id="2" data-pager_step="10" data-allow_composer="1" data-two_columns="false">
                                        <div id="chatterRoot"></div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                    <div class="oe_structure mb32" id="oe_structure_portal_sidebar_1" data-oe-model="ir.ui.view" data-oe-id="561" data-oe-field="arch" data-oe-xpath="/t[1]/t[1]/body[1]/div[2]"></div>
                </div>
            </div>
            <div id="o_shared_blocks" class="oe_unremovable" data-oe-id="962" data-oe-xpath="/data/xpath/div" data-oe-model="ir.ui.view" data-oe-field="arch"></div>
            <div id="o_search_modal_block">
                <div class="modal fade css_editable_mode_hidden" id="o_search_modal" aria-hidden="true" tabindex="-1">
                    <div class="modal-dialog modal-lg pt-5">
                        <div class="modal-content mt-5">
                            <form method="get" class="o_searchbar_form s_searchbar_input" action="/website/search" data-snippet="s_searchbar_input">
                                <div role="search" class="input-group input-group-lg">
                                    <input type="search" name="search" data-oe-model="ir.ui.view" data-oe-id="1019" data-oe-field="arch" data-oe-xpath="/data/xpath[3]/form/t[1]/div[1]/input[1]" class="search-query form-control oe_search_box border border-end-0 p-3 border-0 bg-light" placeholder="Search..." data-search-type="all" data-limit="5" data-display-image="true" data-display-description="true" data-display-extra-link="true" data-display-detail="true" data-order-by="name asc" autocomplete="off">
                                    <button type="submit" aria-label="Search" title="Search" class="btn oe_search_button border border-start-0 px-4 bg-o-color-4">
                                    <i class="oi oi-search" data-oe-model="ir.ui.view" data-oe-id="1019" data-oe-field="arch" data-oe-xpath="/data/xpath[3]/form/t[1]/div[1]/button[1]/i[1]"></i>
                                    </button>
                                </div>
                                <input name="order" type="hidden" class="o_search_order_by" data-oe-model="ir.ui.view" data-oe-id="1019" data-oe-field="arch" data-oe-xpath="/data/xpath[3]/form/input[1]" value="name asc">
                            </form>
                        </div>
                    </div>
                </div>
            </div>
        </main>
        <footer style="height: 50px;"></footer>
    </div>`);
    expect(core.interactions).toHaveLength(1);
    expect(queryOne("#pay_with")).toBeInstanceOf(HTMLElement);
    await advanceTime(400);
    expect("#pay_with").not.toHaveStyle({ "display": "none" });
});
